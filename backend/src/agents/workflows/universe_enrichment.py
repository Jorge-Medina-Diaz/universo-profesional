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
from src.graph.domain import schema as graph_schema
from src.shared.config import get_settings
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

Given a free-text message from a user (in Spanish or English), extract ALL
structured entities mentioned — explicit AND implicit. The user is chatting
naturally; your job is to surface the professional knowledge buried in their
words.

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
  1. Extract EVERY relation explicitly stated or strongly implied.
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
            await universe_graph_service._execute_cypher(
                session,
                f"""
                SELECT * FROM cypher('{graph_schema.GRAPH_PERSONAL}', $$
                    MATCH (e {{id: $eid, user_id: $uid}})
                    SET e.esco_uri = $uri
                    RETURN e.id
                $$) AS (id agtype)
                """,
                {"eid": str(entity_id), "uid": str(user_id), "uri": result.esco_uri},
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
                upserted_id = await self._upsert_entity(ent, source, resolve_duplicates)
                if upserted_id:
                    entity_id_map[(ent.kind, self._canonical_name(ent))] = upserted_id
                    result.entities_created += 1
                    # 3b. Link to ESCO ontology
                    if link_esco:
                        result.esco_linked += await _try_link_esco(
                            self._session, ent, upserted_id, self._user_id
                        )
            except Exception as exc:
                result.errors.append(f"{ent.kind} upsert failed: {exc}")
                logger.warning("enrichment_entity_failed", kind=ent.kind, error=str(exc))

        # 4. Materialise relations as graph edges
        for rel in relations:
            try:
                src_id = entity_id_map.get((rel.source_kind, rel.source_name))
                tgt_id = entity_id_map.get((rel.target_kind, rel.target_name))
                if src_id and tgt_id:
                    await universe_graph_service.upsert_edge(
                        self._session,
                        edge_type=rel.edge_type,
                        source_id=src_id,
                        target_id=tgt_id,
                        user_id=self._user_id,
                        properties=rel.properties,
                        source=source,
                    )
                    result.relations_created += 1
            except Exception as exc:
                result.errors.append(f"relation failed: {exc}")
                logger.warning("enrichment_relation_failed", error=str(exc))

        # 5. Full-graph enrichment (infer RELATED_TO, USES_TECH from tech_stack,
        # etc.). DEBOUNCED off the chat turn (R15 s2): we enqueue a coalesced
        # background job rather than paying the graph-wide cost on every message.
        # If the queue is unreachable we fall back to running it inline on this
        # session so enrichment NEVER silently stops.
        try:
            from src.universe.infrastructure.scheduler import (  # noqa: PLC0415
                enqueue_graph_enrichment,
            )

            enqueued = await enqueue_graph_enrichment(self._user_id)
            if not enqueued:
                from src.universe.application.enrichment import (  # noqa: PLC0415
                    enrich_user_graph,
                )

                await enrich_user_graph(self._session, self._user_id)
                logger.info(
                    "enrichment_graph_enrich_inline_fallback", user_id=str(self._user_id)
                )
        except Exception as exc:
            logger.warning("enrichment_graph_enrich_failed", error=str(exc))

        logger.info(
            "universe_enriched",
            user_id=str(self._user_id),
            entities_created=result.entities_created,
            relations_created=result.relations_created,
            errors=len(result.errors),
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
        try:
            parsed = json.loads(response)
            if not isinstance(parsed, list):
                return []
            return [
                ExtractedEntity(kind=e["kind"], payload=e.get("payload", {}), confidence=e.get("confidence", 0.9))
                for e in parsed
                if "kind" in e and "payload" in e
            ]
        except json.JSONDecodeError:
            fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", response, re.DOTALL)
            if fence:
                try:
                    parsed = json.loads(fence.group(1))
                    return [
                        ExtractedEntity(kind=e["kind"], payload=e.get("payload", {}))
                        for e in parsed
                        if "kind" in e
                    ]
                except json.JSONDecodeError:
                    pass
            logger.warning("entity_extraction_parse_failed", response=response[:200])
            return []

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
        try:
            parsed = json.loads(response)
            if not isinstance(parsed, list):
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
                if all(k in r for k in ("source_kind", "source_name", "edge_type", "target_kind", "target_name"))
            ]
        except json.JSONDecodeError:
            logger.warning("relation_extraction_parse_failed", response=response[:200])
            return []

    # Upsert

    async def _upsert_entity(
        self, ent: ExtractedEntity, source: str, resolve: bool
    ) -> UUID | None:
        """Upsert through the coherence engine."""
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

        if outcome.status in (UpsertStatus.CREATED, UpsertStatus.MERGED):
            return outcome.entity_id
        if outcome.status == UpsertStatus.SUGGESTED:
            # We still return the suggested entity_id if available
            return outcome.entity_id
        return None

    # Helpers

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
        from anthropic import AsyncAnthropic  # noqa: PLC0415

        client = AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        system = messages[0]["content"]
        user_msgs = [m for m in messages[1:] if m["role"] == "user"]
        response = await client.messages.create(
            model=self._settings.agents_specialist_model or "claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": m["content"]} for m in user_msgs],
        )
        return str(response.content[0].text)

    async def _call_openai(self, messages: list[dict[str, str]]) -> str:
        from openai import AsyncOpenAI  # noqa: PLC0415

        client = AsyncOpenAI(api_key=self._settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=2048,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        return str(response.choices[0].message.content)
