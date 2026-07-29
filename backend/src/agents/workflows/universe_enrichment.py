"""Universe Enrichment Engine — turn free-text into structured graph nodes & edges.

When the user chatters, imports a CV, or dictates their history, this engine:
  1. Extracts structured entities (experiences, skills, projects, etc.)
  2. Extracts typed relations between them ("used X in Y", "learned Z at W")
  3. Resolves duplicates via Entity Resolution v2
  4. Materialises nodes + edges in AGE
  5. Links skills to ESCO where possible

The result is a living graph that grows with every conversation.
"""
from __future__ import annotations

import contextlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal, cast
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.domain.sources import SOURCE_AGENT_CHAT
from src.coherence.application.upsert_use_cases import UpsertUniverseEntity
from src.coherence.domain.upsert_decision import UpsertStatus
from src.coherence.infrastructure.change_log_repo import SqlAlchemyChangeLogRepository
from src.coherence.infrastructure.semantic_matcher import PgVectorSemanticMatcher
from src.graph.application.esco_linker import LinkState, esco_linker
from src.graph.application.universe_graph import universe_graph_service
from src.shared.config import get_settings
from src.shared.llm_client import anthropic_text
from src.shared.metrics import discovery_entities_extracted_total
from src.shared.uow import UnitOfWork

logger = structlog.get_logger(__name__)


# Domain types


@dataclass
class ExtractedEntity:
    kind: str
    payload: dict[str, Any]
    confidence: float = 0.9


@dataclass
class ExtractedRelation:
    source_kind: str
    source_name: str
    edge_type: str
    target_kind: str
    target_name: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnrichmentResult:
    entities_created: int = 0
    entities_merged: int = 0
    relations_created: int = 0
    esco_linked: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# LLM prompts
# ---------------------------------------------------------------------------

_ENTITY_EXTRACTION_PROMPT = """You are an expert professional-profile extractor for a knowledge-graph system.

You receive either a free-text message OR a conversation transcript
("Usuario:"/"Agente:" lines, the last user line marked as FOCO). Extract ALL
structured entities — explicit AND implicit. The user is chatting naturally;
your job is to surface the professional knowledge buried in their words.

Transcript rules (when the input is a conversation):
  • SYNTHESIZE ACROSS TURNS: details scattered over several turns belong to
    ONE entity. If the user said "monté un ecommerce" three turns ago, "con
    Next.js y Stripe" later and "el catálogo lo genera una IA" after that,
    that is ONE project with tech_stack ["Next.js","Stripe","IA generativa"]
    and a highlight about the AI catalog — NOT three fragments.
  • The FOCO line is what's new; earlier turns give it context and details.
  • Extract ONLY what the USER asserts. The agent's lines are context — never
    extract from agent suggestions or questions the user did not confirm.
  • Personal context that frames a project ("para la tienda de mi hermana")
    belongs in the entity description, it is not an entity itself.
  • Learnings deserve their own entities: "aprendí mucho de X peleándome con
    Y" → skill X + achievement (title: what was learned, context: Y).
  • BE EXHAUSTIVE: a rich 5-turn story should typically yield 5-10 entities
    (the project, every technology as a skill, the learnings, achievements)
    with FULL payloads (tech_stack, highlights, competences, descriptions).

Supported kinds and fields:
  experience   — {organization, role, start_date, end_date, description, highlights[], competences[], employment_type, location}
  education    — {institution, degree, field_of_study, start_date, end_date, description}
  skill        — {name, category (hard/soft/tool/methodology), level (basic/intermediate/high/expert), years}
  project      — {name, description, tech_stack[], highlights[], role, url}
  certification — {name, issuer, issued_on, expires_on, credential_id}
  course       — {title, platform, completed_on, duration_hours}
  language     — {code, name, level (A1/A2/B1/B2/C1/C2/native)}
  achievement  — {title, achieved_on, description, context}
  interest     — {name, description}

Extraction rules:
  1. IMPLICIT ENTITIES — extract everything implied, not just stated:
     • "usé Python y React" → skill "Python", skill "React" + experience (implicit)
     • "lideré un equipo de 5" → skill "Liderazgo de equipos", skill "Gestión de personas"
     • "reduje costes un 30%" → achievement "Reducción de costes 30%"
     • "hablo inglés fluido" → language "Inglés" level "C2"
     • "estoy aprendiendo Go" → skill "Go" level "basic" + interest "Go"
     • "hice un curso de AWS en Udemy" → course "AWS" platform "Udemy" + skill "AWS"
  2. DATES — normalise to ISO-8601 (YYYY-MM-DD) or year (YYYY):
     • "desde 2022" → start_date "2022"
     • "hace 3 años" → start_date "2023" (current year 2026)
     • "actualmente / presente" → end_date null (ongoing)
     • "enero-marzo 2024" → start_date "2024-01" end_date "2024-03"
     • If only a year range is known, use YYYY only.
  3. COMPETENCES / HIGHLIGHTS — when the user describes impact or responsibilities,
     break them into atomic items:
     • "diseñé la arquitectura, optimicé queries, mentoría a juniors" →
       competences ["Diseño de arquitectura", "Optimización de queries", "Mentoría"]
  4. NEVER guess — if a field is unknown, omit it.
  5. Return ONLY a JSON array: [{"kind": "...", "payload": {...}, "confidence": 0.9}, ...]
     • confidence: 1.0 = explicit, 0.8 = strongly implied, 0.6 = weakly implied
  6. If no entities found, return [].

Examples:
Input: "Trabajé en Google como senior dev desde 2020, usé Python y Kubernetes."
Output:
[
  {"kind": "experience", "payload": {"organization": "Google", "role": "Senior Developer", "start_date": "2020"}, "confidence": 1.0},
  {"kind": "skill", "payload": {"name": "Python", "category": "hard", "level": "high"}, "confidence": 1.0},
  {"kind": "skill", "payload": {"name": "Kubernetes", "category": "tool", "level": "high"}, "confidence": 1.0}
]

Input: "Lideré la migración a microservicios, reduciendo latency un 40%."
Output:
[
  {"kind": "project", "payload": {"name": "Migración a microservicios", "description": "Lideré la migración a microservicios", "highlights": ["Reducción de latencia 40%"]}, "confidence": 0.9},
  {"kind": "skill", "payload": {"name": "Liderazgo técnico", "category": "soft", "level": "high"}, "confidence": 0.8},
  {"kind": "skill", "payload": {"name": "Arquitectura de microservicios", "category": "methodology", "level": "high"}, "confidence": 0.8},
  {"kind": "achievement", "payload": {"title": "Reducción de latencia 40%", "description": "Reducción de latencia en migración a microservicios"}, "confidence": 0.8}
]
"""

def _norm(name: str) -> str:
    return " ".join((name or "").lower().split())


def _load_json_array(response: str) -> list:
    """Best-effort parse of an LLM response that SHOULD be a JSON array.

    Handles every shape the extraction has hit in the wild, none of which the
    naive json.loads covered:
      1. a bare JSON array (the happy path);
      2. an array wrapped in ```json fences``` (Anthropic's usual habit);
      3. a top-level OBJECT like {"entities": [...]} — OpenAI's json_object
         response_format forces this, and the old code dropped it as "not a
         list" with NO log, so extraction was permanently empty on OpenAI;
      4. a TRUNCATED array (hit max_tokens mid-element) — recovered by scanning
         to the last COMPLETE top-level object and closing the bracket, so a
         long turn keeps the entities it did finish instead of losing them all.
    Returns [] only when nothing salvageable is found.
    """
    if not response:
        return []
    s = response.strip()
    # 2. strip a leading/closing fence if present (closing optional).
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
        s = s.strip()
    # 1. direct parse.
    try:
        parsed = json.loads(s)
    except json.JSONDecodeError:
        parsed = None
    # 3. object-wrapped array → first list value.
    if isinstance(parsed, dict):
        for v in parsed.values():
            if isinstance(v, list):
                return v
        return []
    if isinstance(parsed, list):
        return parsed
    # 4. truncation salvage: take from the first '[' and append closing
    # brackets after the last balanced '}'.
    start = s.find("[")
    if start == -1:
        return []
    depth = 0
    last_complete = -1
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
            if depth == 1 and ch == "}":
                last_complete = i
    if last_complete > start:
        try:
            return json.loads(s[start : last_complete + 1] + "]")
        except json.JSONDecodeError:
            return []
    return []


_KIND_SQL: dict[str, tuple[str, str]] = {
    "experience": ("experiences", "organization"),
    "education": ("educations", "institution"),
    "skill": ("skills", "name"),
    "project": ("projects", "name"),
    "certification": ("certifications", "name"),
    "course": ("courses", "title"),
    "language": ("languages", "name"),
    "achievement": ("achievements", "title"),
    "interest": ("interests", "name"),
}


_RELATION_EXTRACTION_PROMPT = """You are a relation extractor for a professional knowledge graph.

Given the user's text and the entities already extracted, identify typed
relationships between them.  Supported edge types:

  USES_TECH      — experience/project → skill ("usé Python en el proyecto X")
  PART_OF        — project → experience ("el proyecto Y fue durante mi trabajo en Z")
  DERIVED_FROM   — skill → project/course ("aprendí React del curso W")
  EVIDENCES_SIGNAL — experience/project → achievement ("reduje costes 30% en proyecto X")
  TOUCHED_IN     — skill → experience ("usé Docker en mi trabajo en Google")
  SUPERSEDES     — skill/skill ("migré de Angular a React" → React SUPERSEDES Angular)
  MEMBER_OF      — project → experience ("como parte del equipo de infra")
  RELATED_TO     — generic relation with a custom label in properties.label

Rules:
  1. Extract EVERY relation explicitly stated or strongly implied BY THE USER.
     The transcript may contain "Agente:" lines — those are context only. NEVER
     create a relation from something only the agent said or proposed; the user
     must have asserted or confirmed it.
  2. If a skill is mentioned in the context of an experience/project, create USES_TECH.
  3. If an achievement/impact is described in the context of a project/experience, create EVIDENCES_SIGNAL.
  4. If a skill replaced another (migración, cambio de stack), create SUPERSEDES.
  5. Return ONLY a JSON array:
     [{"source_kind": "...", "source_name": "...", "edge_type": "USES_TECH", "target_kind": "...", "target_name": "...", "properties": {}}, ...]
  6. If no relations, return [].

Examples:
Input: "En Google usé Python y Kubernetes para el proyecto Search v2."
Entities: experience "Google", project "Search v2", skill "Python", skill "Kubernetes"
Output:
[
  {"source_kind": "experience", "source_name": "google", "edge_type": "USES_TECH", "target_kind": "skill", "target_name": "python"},
  {"source_kind": "experience", "source_name": "google", "edge_type": "USES_TECH", "target_kind": "skill", "target_name": "kubernetes"},
  {"source_kind": "project", "source_name": "search v2", "edge_type": "PART_OF", "target_kind": "experience", "target_name": "google"}
]
"""


# ESCO linking helper


async def _try_link_esco(
    session: AsyncSession,
    ent: ExtractedEntity,
    entity_id: UUID,
    user_id: UUID,
) -> int:
    """Try to link an entity to the ESCO ontology. Returns 1 if linked, 0 otherwise."""
    kind_map = {
        "skill": "skill",
        "experience": "occupation",
        "language": None,
    }
    esco_kind = kind_map.get(ent.kind)
    if not esco_kind:
        return 0

    if ent.kind == "skill":
        link_text = ent.payload.get("name", "")
    elif ent.kind == "experience":
        link_text = f"{ent.payload.get('role', '')} {ent.payload.get('organization', '')}"
    else:
        return 0

    if not link_text.strip():
        return 0

    try:
        result = await esco_linker.link(
            session,
            text_in=link_text,
            kind=cast(Literal["skill", "occupation"], esco_kind),
        )
        if result.state == LinkState.LINKED and result.esco_uri:
            target_label = "EscoSkill" if esco_kind == "skill" else "Occupation"
            # SAVEPOINT: a failure in either write (INSERT or the AGE cypher SET)
            # must roll back ONLY this ESCO link, not the whole pass. Without
            # the savepoint a failure left the asyncpg tx aborted, so the NEXT
            # entity's first query died with InFailedSQLTransactionError and its
            # data was lost (#19/#22/#40).
            async with session.begin_nested():
                await session.execute(
                    text("""
                        INSERT INTO graph_esco_links
                            (user_id, entity_id, esco_uri, target_label, score)
                        VALUES (:uid, :eid, :uri, :tgt, :score)
                        ON CONFLICT (user_id, entity_id, esco_uri) DO UPDATE
                          SET score = EXCLUDED.score,
                              target_label = EXCLUDED.target_label
                    """),
                    {
                        "uid": str(user_id),
                        "eid": str(entity_id),
                        "uri": result.esco_uri,
                        "tgt": target_label,
                        "score": round(result.score or 0.0, 3),
                    },
                )
                # The graph repo wraps the fragment in SELECT * FROM cypher(...)
                # itself — passing a pre-wrapped statement double-wrapped it into
                # "syntax error at or near SELECT".
                await universe_graph_service._execute_cypher(
                    session,
                    """
                    MATCH (e {id: $eid, user_id: $uid})
                    SET e.esco_uri = $uri
                    RETURN e.id
                    """,
                    {"eid": str(entity_id), "uid": str(user_id), "uri": result.esco_uri},
                    column_defs="id agtype",
                )
            logger.info(
                "esco_linked",
                user_id=str(user_id),
                entity_id=str(entity_id),
                kind=ent.kind,
                uri=result.esco_uri,
                score=result.score,
            )
            return 1
        if result.state == LinkState.SUGGESTED:
            logger.info(
                "esco_suggested",
                user_id=str(user_id),
                entity_id=str(entity_id),
                kind=ent.kind,
                top_score=result.score,
            )
    except Exception as exc:
        logger.warning("esco_link_failed", error=str(exc), kind=ent.kind, text=link_text[:50])
    return 0


# Engine


class UniverseEnrichmentEngine:
    """Process free text and grow the user's professional graph."""

    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self._session = session
        self._user_id = user_id
        self._settings = get_settings()

    async def process(
        self,
        text: str,
        *,
        source: str = SOURCE_AGENT_CHAT,
        resolve_duplicates: bool = True,
        link_esco: bool = True,
    ) -> EnrichmentResult:
        """Run the full enrichment pipeline on *text*."""
        result = EnrichmentResult()

        if not text or not text.strip():
            return result

        # 1. Extract entities
        entities = await self._extract_entities(text)
        if not entities:
            return result

        for ent in entities:
            discovery_entities_extracted_total.labels(kind=ent.kind).inc()

        # 2. Extract relations
        relations = await self._extract_relations(text, entities)

        # 3. Upsert entities (with ER v2 + ESCO linking)
        entity_id_map: dict[tuple[str, str], UUID] = {}
        for ent in entities:
            try:
                upserted_id, status = await self._upsert_entity(
                    ent, source, resolve_duplicates
                )
                if upserted_id:
                    entity_id_map[
                        (ent.kind, _norm(self._canonical_name(ent)))
                    ] = upserted_id
                    # Honest accounting: CREATED vs MERGED were both counted as
                    # "created" before, so entities_merged was always 0.
                    if status == UpsertStatus.MERGED:
                        result.entities_merged += 1
                    else:
                        result.entities_created += 1
                    # Embed INLINE so the very next turn's semantic dedup can
                    # see this row. The async refresh lands too late: the
                    # turn-1 fragment had no embedding when turn-3's rich
                    # version arrived, so the matcher created a duplicate. Uses
                    # its own session — the entity is already committed by
                    # _upsert_entity, so the embed read sees it.
                    try:
                        from src.universe.infrastructure.tasks import (
                            refresh_embedding,
                        )

                        await refresh_embedding(
                            {}, entity_type=ent.kind, entity_id=str(upserted_id)
                        )
                    except Exception as exc:  # embedding lag is tolerable
                        logger.debug("inline_embedding_failed", error=str(exc))
                    # 3b. Link to ESCO ontology (savepoint-isolated), then COMMIT
                    # so the link is durable and a later failure can't roll it
                    # back (#6/#8: each unit of work commits independently).
                    if link_esco:
                        linked = await _try_link_esco(
                            self._session, ent, upserted_id, self._user_id
                        )
                        result.esco_linked += linked
                        if linked:
                            await self._session.commit()
            except Exception as exc:
                result.errors.append(f"{ent.kind} upsert failed: {exc}")
                logger.warning("enrichment_entity_failed", kind=ent.kind, error=str(exc))
                # Recover the session for the next entity. Prior entities are
                # already committed, so this only discards the failed one.
                with contextlib.suppress(Exception):  # pragma: no cover
                    await self._session.rollback()

        # 4. Materialise relations as graph edges. Endpoints resolve against
        # this pass's map first, then against the user's EXISTING entities —
        # otherwise a new skill could never link to the project mentioned
        # three turns ago (relations_created was permanently 0 for those).
        for rel in relations:
            try:
                src_id = entity_id_map.get(
                    (rel.source_kind, _norm(rel.source_name))
                ) or await self._resolve_existing(rel.source_kind, rel.source_name)
                tgt_id = entity_id_map.get(
                    (rel.target_kind, _norm(rel.target_name))
                ) or await self._resolve_existing(rel.target_kind, rel.target_name)
                if not (src_id and tgt_id):
                    # Endpoint(s) unresolved — log it instead of dropping the
                    # relation in total silence (it used to vanish with no
                    # record at all, so a missing edge looked like "nothing to
                    # connect" when it was really an unresolved name).
                    logger.info(
                        "enrichment_relation_unresolved",
                        edge=rel.edge_type,
                        src=f"{rel.source_kind}:{rel.source_name}"[:60],
                        tgt=f"{rel.target_kind}:{rel.target_name}"[:60],
                        src_ok=bool(src_id),
                        tgt_ok=bool(tgt_id),
                    )
                    continue
                # SAVEPOINT + COMMIT per edge: a failing edge rolls back only
                # itself and the successful ones are already durable, so one bad
                # edge can no longer silently destroy the edges before it.
                async with self._session.begin_nested():
                    await universe_graph_service.upsert_edge(
                        self._session,
                        edge_type=rel.edge_type,
                        source_id=src_id,
                        target_id=tgt_id,
                        user_id=self._user_id,
                        properties=rel.properties,
                        source=source,
                    )
                await self._session.commit()
                result.relations_created += 1
            except Exception as exc:
                result.errors.append(f"relation failed: {exc}")
                logger.warning("enrichment_relation_failed", error=str(exc))
                with contextlib.suppress(Exception):  # pragma: no cover
                    await self._session.rollback()

        # 5. Full-graph enrichment (infer RELATED_TO, USES_TECH from tech_stack,
        # etc.). DEBOUNCED off the chat turn (R15 s2): we enqueue a coalesced
        # background job rather than paying the graph-wide cost on every message.
        # If the queue is unreachable we fall back to running it inline on this
        # session so enrichment NEVER silently stops.
        try:
            from src.universe.infrastructure.scheduler import (
                enqueue_graph_enrichment,
            )

            enqueued = await enqueue_graph_enrichment(self._user_id)
            if not enqueued:
                from src.universe.application.enrichment import (
                    enrich_user_graph,
                )

                await enrich_user_graph(self._session, self._user_id)
                logger.info(
                    "enrichment_graph_enrich_inline_fallback", user_id=str(self._user_id)
                )
        except Exception as exc:
            logger.warning("enrichment_graph_enrich_failed", error=str(exc))

        # Lost user data (an entity/relation that failed to persist) is a real
        # failure — log it at ERROR with the messages so it's visible in
        # monitoring/Sentry, not buried in an info line that says "errors=2".
        log = logger.error if result.errors else logger.info
        log(
            "universe_enriched",
            user_id=str(self._user_id),
            entities_created=result.entities_created,
            entities_merged=result.entities_merged,
            relations_created=result.relations_created,
            errors=len(result.errors),
            error_detail=result.errors[:5] if result.errors else None,
        )
        return result

    # Extraction

    async def _extract_entities(self, text: str) -> list[ExtractedEntity]:
        """Call LLM to extract structured entities from text."""
        response = await self._call_llm(
            [
                {"role": "system", "content": _ENTITY_EXTRACTION_PROMPT},
                {"role": "user", "content": text},
            ]
        )
        parsed = _load_json_array(response)
        if not parsed:
            logger.warning("entity_extraction_parse_failed", response=response[:200])
            return []
        # ONE consistent filter+confidence path (the old fenced fallback dropped
        # confidence — inflating a 0.6 to 0.9 — and accepted payload-less
        # entities that became empty CREATE noops).
        return [
            ExtractedEntity(
                kind=e["kind"],
                payload=e.get("payload", {}),
                confidence=e.get("confidence", 0.9),
            )
            for e in parsed
            if isinstance(e, dict) and e.get("kind") and e.get("payload")
        ]

    async def _extract_relations(
        self, text: str, entities: list[ExtractedEntity]
    ) -> list[ExtractedRelation]:
        """Call LLM to extract typed relations."""
        entity_summary = json.dumps(
            [{"kind": e.kind, "name": self._canonical_name(e)} for e in entities],
            ensure_ascii=False,
        )
        response = await self._call_llm(
            [
                {"role": "system", "content": _RELATION_EXTRACTION_PROMPT},
                {"role": "user", "content": f"TEXT:\n{text}\n\nENTITIES:\n{entity_summary}"},
            ]
        )
        parsed = _load_json_array(response)
        if not parsed:
            logger.warning("relation_extraction_parse_failed", response=response[:200])
            return []
        return [
            ExtractedRelation(
                source_kind=r["source_kind"],
                source_name=r["source_name"],
                edge_type=r["edge_type"],
                target_kind=r["target_kind"],
                target_name=r["target_name"],
                properties=r.get("properties", {}),
            )
            for r in parsed
            if isinstance(r, dict)
            and all(
                k in r
                for k in (
                    "source_kind",
                    "source_name",
                    "edge_type",
                    "target_kind",
                    "target_name",
                )
            )
        ]

    # Upsert

    async def _upsert_entity(
        self, ent: ExtractedEntity, source: str, resolve: bool
    ) -> tuple[UUID | None, UpsertStatus | None]:
        """Upsert through the coherence engine. Returns (entity_id, status)."""
        matcher = PgVectorSemanticMatcher(self._session)
        change_log = SqlAlchemyChangeLogRepository(self._session)
        uc = UpsertUniverseEntity(self._session, change_log=change_log, semantic_matcher=matcher)

        uow = UnitOfWork(self._session)
        outcome = await uc.execute(
            entity_type=ent.kind,
            user_id=str(self._user_id),
            payload=ent.payload,
            uow=uow,
            source=source,
        )
        await uow.commit()

        if outcome.status in (
            UpsertStatus.CREATED,
            UpsertStatus.MERGED,
            UpsertStatus.SUGGESTED,
        ):
            return outcome.entity_id, outcome.status
        return None, outcome.status

    # Helpers

    async def _resolve_existing(self, kind: str, name: str) -> UUID | None:
        """Find an existing entity of *kind* whose display name matches *name*
        (case/whitespace-insensitive). Lets relations connect new facts to
        entities created in earlier turns or imports."""
        from sqlalchemy import text as _text

        spec = _KIND_SQL.get(kind)
        if not spec or not name:
            return None
        table, field = spec
        # Match _norm exactly: lower + collapse ALL internal whitespace runs to
        # one space. Plain trim() only strips the ENDS, so a stored "Search  v2"
        # (double space — common in LLM/CV payloads) never equalled _norm's
        # "search v2" and its relations were silently dropped (#37/#41).
        return (
            await self._session.execute(
                _text(
                    f"SELECT id FROM {table} WHERE user_id = :uid "
                    f"AND deleted_at IS NULL "
                    f"AND lower(regexp_replace(trim({field}), '\\s+', ' ', 'g')) = :name "
                    "ORDER BY updated_at DESC LIMIT 1"
                ),
                {"uid": str(self._user_id), "name": _norm(name)},
            )
        ).scalar()

    def _canonical_name(self, ent: ExtractedEntity) -> str:
        """Return a stable name key for the entity (used in relation mapping)."""
        p = ent.payload
        name_fields = {
            "experience": "organization",
            "education": "institution",
            "skill": "name",
            "project": "name",
            "certification": "name",
            "course": "title",
            "language": "name",
            "achievement": "title",
            "interest": "name",
        }
        field = name_fields.get(ent.kind, "name")
        return str(p.get(field) or p.get("name") or p.get("title") or "").strip().lower()

    async def _call_llm(self, messages: list[dict[str, str]]) -> str:
        """Route to the configured LLM provider."""
        provider = self._settings.agents_provider_resolved
        if provider == "anthropic":
            return await self._call_anthropic(messages)
        if provider == "openai":
            return await self._call_openai(messages)
        # Mock fallback
        return "[]"

    async def _call_anthropic(self, messages: list[dict[str, str]]) -> str:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        system = messages[0]["content"]
        user_msgs = [m for m in messages[1:] if m["role"] == "user"]
        response = await client.messages.create(
            model=self._settings.agents_specialist_model or "claude-haiku-4-5-20251001",
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": m["content"]} for m in user_msgs],
        )
        return anthropic_text(response.content)

    async def _call_openai(self, messages: list[dict[str, str]]) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._settings.openai_api_key)
        # NOTE: response_format json_object would force a top-level OBJECT, but
        # both extraction prompts demand a JSON ARRAY — the mismatch made every
        # OpenAI extraction parse to [] silently. We leave the format free and
        # let _load_json_array handle whatever shape comes back (incl. an
        # accidentally object-wrapped array).
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=8192,
            temperature=0.1,
        )
        return str(response.choices[0].message.content)
