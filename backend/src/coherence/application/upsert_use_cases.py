"""Upsert orchestrator — central pipeline used by every agent write.

Flow:
  1. find_existing(entity_type, payload) — by exact name when available,
     fall back to semantic similarity.
  2. No match → call the existing `*Crud.add` use case and record a `create`.
  3. Match → run the entity-specific merge rule (`merge_rules.py`). If the
     merge needs user confirmation (e.g., conflicting category for a skill),
     emit a `suggestion` row and return SUGGESTED without mutating. Otherwise
     apply the merged payload via `*Crud.update`, record one row per field
     diff in `universe_change_log`, and link evidence.

The orchestrator does NOT duplicate validation: the underlying CRUDs use the
entity `.create()` / `.update()` paths which already raise `ValidationError`.

Entity metadata (name_field, embedding_text, table, supports_stale, …)
lives in the single `GRAPH_REGISTRY` source of truth
(`src.graph.domain.registry`). This module only adds the CRUD/repo
wiring (`_CRUD_WIRING`) that can't live in a domain module, and builds
`_DISPATCH` from both. `mark_stale`, `curator` and `signal_extraction`
read `GRAPH_REGISTRY` directly.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.coherence.application.change_log import (
    record_create,
    record_merge,
)
from src.coherence.application.ports import (
    ChangeLogRepository,
    SemanticMatcher,
)
from src.coherence.domain.merge_rules import merge_for
from src.coherence.domain.upsert_decision import (
    MatchKind,
    MatchResult,
    UpsertOutcome,
    UpsertStatus,
)
from src.graph.application.universe_graph import universe_graph_service
from src.graph.domain.registry import GRAPH_REGISTRY
from src.shared.uow import UnitOfWork
from src.universe.application.registry import CrudRegistry
from src.universe.application.use_cases import _serialize
from src.universe.infrastructure.scheduler import ArqEmbeddingScheduler

_log = structlog.get_logger(__name__)


# `_DISPATCH` is the per-upsert config: graph-registry metadata + the
# CRUD/repo wiring from the central ``CrudRegistry``. Built once so the
# two can never drift.
_DISPATCH: dict[str, dict[str, Any]] = {
    kind: {
        "crud": CrudRegistry.get_crud_class(kind),
        "repo": CrudRegistry.get_repo_class(kind),
        "name_field": cfg.name_field,
        "table": cfg.sql_table,
        "embedding_text": cfg.embedding_text,
    }
    for kind, cfg in GRAPH_REGISTRY.items()
    if kind in CrudRegistry.kinds()
}


# Date columns across the entity kinds. Agents (and partial human input)
# routinely emit a year only ('2023') or year-month ('2023-06') for these,
# but the columns are SQL DATE → asyncpg needs a real date object. We coerce
# partial strings at the single write funnel below so every path (chat, REST,
# import) is safe.
_DATE_FIELDS: frozenset[str] = frozenset(
    {"start_date", "end_date", "issued_on", "expires_on", "completed_on"}
)


def _parse_partial_date(value: str):  # type: ignore[no-untyped-def]
    from datetime import date

    s = value.strip()
    if not s:
        return None
    parts = s.split("-")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 and parts[1] else 1
        day = int(parts[2]) if len(parts) > 2 and parts[2] else 1
        return date(year, month, day)
    except (ValueError, IndexError):
        try:
            return date.fromisoformat(s)
        except ValueError:
            return None


def _coerce_date_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Turn partial date strings into date objects for DATE columns.

    Unparseable strings (e.g. 'present') become None — the right semantic for
    an open-ended date — rather than crashing the INSERT.
    """
    out = dict(payload)
    for field in _DATE_FIELDS:
        val = out.get(field)
        if isinstance(val, str):
            out[field] = _parse_partial_date(val)
    return out


def is_known_entity(entity_type: str) -> bool:
    return entity_type in _DISPATCH


def entities_supporting_stale() -> list[str]:
    """Entity kinds the curator may mark stale (reads GRAPH_REGISTRY)."""
    return [k for k, cfg in GRAPH_REGISTRY.items() if cfg.supports_stale]


# Semantic similarity thresholds. Anything ≥ AUTO_MERGE is fused silently;
# between AMBIGUOUS_LOW and AUTO_MERGE → suggestion; below → considered no match.
AUTO_MERGE_THRESHOLD = 0.92
AMBIGUOUS_LOW = 0.80


async def _adaptive_ambiguous_low(session: AsyncSession, user_id: str) -> float:
    """Lower AMBIGUOUS_LOW for users who historically accept many merges
    in the 0.82-0.90 score band (read from universe_change_log).

    This is a lightweight, privacy-preserving heuristic: we only look at
    the *ratio* of recent merges whose reason contains a semantic score in
    the band, not at the actual entity contents.
    """
    rows = await session.execute(
        text(
            """
            SELECT reason FROM universe_change_log
            WHERE user_id = :uid
              AND change_type IN ('merge', 'create')
              AND changed_at > now() - interval '30 days'
            ORDER BY changed_at DESC
            LIMIT 100
            """
        ),
        {"uid": user_id},
    )
    scores: list[float] = []
    for row in rows.all():
        reason = row.reason or ""
        if "[semantic " in reason:
            try:
                score_str = reason.split("[semantic ")[1].split("]")[0]
                scores.append(float(score_str))
            except (ValueError, IndexError):
                continue

    if not scores:
        return AMBIGUOUS_LOW

    band_scores = [s for s in scores if 0.82 <= s <= 0.90]
    if not band_scores:
        return AMBIGUOUS_LOW

    # If >90 % of recent actions involve scores in the ambiguous-like band,
    # the user is highly accepting — lower the floor so more candidates surface.
    band_ratio = len(band_scores) / len(scores)
    if band_ratio > 0.90:
        return max(0.70, AMBIGUOUS_LOW - 0.05)

    return AMBIGUOUS_LOW


class UpsertUniverseEntity:
    """Single entry point. Pass `entity_type` + payload + source; get an outcome."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        change_log: ChangeLogRepository,
        semantic_matcher: SemanticMatcher,
    ) -> None:
        self._session = session
        self._change_log = change_log
        self._matcher = semantic_matcher
        self._scheduler = ArqEmbeddingScheduler()

    async def execute(
        self,
        *,
        entity_type: str,
        user_id: str,
        payload: dict[str, Any],
        uow: UnitOfWork,
        source: str = "agent_chat",
        agent_run_id: str | None = None,
        chat_session_id: str | None = None,
        op_hint: str | None = None,
    ) -> UpsertOutcome:
        # Mem0-style write contract: when the agent has reasoned that the
        # turn should NOT mutate the universe, it passes op_hint='NOOP'.
        # We honour it as a hard short-circuit. ADD / UPDATE / DELETE
        # remain advisory — the coherence engine auto-detects the right
        # path (create vs merge) below.
        if op_hint == "NOOP":
            return UpsertOutcome(
                status=UpsertStatus.NOOP, entity_id=None, reason="agent op_hint=NOOP"
            )

        if entity_type not in _DISPATCH:
            return UpsertOutcome(
                status=UpsertStatus.NOOP,
                entity_id=None,
                reason=f"unknown entity_type {entity_type!r}",
            )

        config = _DISPATCH[entity_type]
        payload = {k: v for k, v in payload.items() if v is not None}
        # Coerce partial date strings ('2023', '2023-06') → date objects.
        payload = _coerce_date_fields(payload)
        payload = {k: v for k, v in payload.items() if v is not None}

        # --- 1. Find existing -------------------------------------------------
        match = await self._find_existing(
            entity_type=entity_type, user_id=user_id, payload=payload, config=config
        )

        # --- 2. No match → create --------------------------------------------
        if not match.has_match and match.kind != MatchKind.AMBIGUOUS:
            return await self._create(
                entity_type=entity_type,
                user_id=user_id,
                payload=payload,
                config=config,
                source=source,
                uow=uow,
                agent_run_id=agent_run_id,
                chat_session_id=chat_session_id,
            )

        # --- 3. Ambiguous → emit suggestion -----------------------------------
        if match.kind == MatchKind.AMBIGUOUS:
            sugg_id = await self._emit_suggestion(
                user_id=user_id,
                entity_type=entity_type,
                candidates=match.candidates,
                payload=payload,
            )
            return UpsertOutcome(
                status=UpsertStatus.SUGGESTED,
                entity_id=None,
                suggestion_id=sugg_id,
                reason="semantic match in ambiguous band — user confirmation needed",
            )

        # --- 4. Match → merge -------------------------------------------------
        assert match.entity_id is not None
        return await self._merge(
            entity_type=entity_type,
            user_id=user_id,
            existing_id=match.entity_id,
            payload=payload,
            config=config,
            source=source,
            uow=uow,
            agent_run_id=agent_run_id,
            chat_session_id=chat_session_id,
            match=match,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _find_existing(
        self,
        *,
        entity_type: str,
        user_id: str,
        payload: dict[str, Any],
        config: dict[str, Any],
    ) -> MatchResult:
        # 1. Exact match by the canonical name field (case-insensitive).
        name_field = config["name_field"]
        name_value = payload.get(name_field)
        if name_value:
            row = (
                await self._session.execute(
                    text(
                        f"SELECT id::text AS id FROM {config['table']} "
                        f"WHERE user_id = :uid AND lower({name_field}) = lower(:n) LIMIT 1"
                    ),
                    {"uid": user_id, "n": str(name_value)},
                )
            ).first()
            if row is not None:
                return MatchResult(kind=MatchKind.EXACT, entity_id=UUID(row.id), score=1.0)

        # 2. Semantic similarity.
        emb_text = config["embedding_text"](payload).strip()
        if not emb_text:
            return MatchResult(kind=MatchKind.NONE)
        ambiguous_low = await _adaptive_ambiguous_low(self._session, user_id)
        hits = await self._matcher.find_most_similar(
            user_id=UUID(user_id),
            entity_type=entity_type,
            text=emb_text,
            threshold=ambiguous_low,
            top_k=3,
        )
        if not hits:
            return MatchResult(kind=MatchKind.NONE)
        top = hits[0]
        if top["score"] >= AUTO_MERGE_THRESHOLD:
            return MatchResult(
                kind=MatchKind.SEMANTIC, entity_id=UUID(top["entity_id"]), score=top["score"]
            )
        # AMBIGUOUS_LOW ≤ score < AUTO_MERGE_THRESHOLD
        return MatchResult(
            kind=MatchKind.AMBIGUOUS,
            candidates=[UUID(h["entity_id"]) for h in hits],
            score=top["score"],
        )

    async def _create(
        self,
        *,
        entity_type: str,
        user_id: str,
        payload: dict[str, Any],
        config: dict[str, Any],
        source: str,
        uow: UnitOfWork,
        agent_run_id: str | None,
        chat_session_id: str | None = None,
    ) -> UpsertOutcome:
        crud = config["crud"](config["repo"](self._session), self._scheduler)
        # Strip our coherence-only fields before handing off to domain entity.
        domain_payload = _strip_metadata_keys(payload)
        # Pipe `source` so universe entities preserve provenance.
        domain_payload.setdefault("source", source)
        result = await crud.add(user_id=user_id, payload=domain_payload, uow=uow)
        if result.is_failure:
            return UpsertOutcome(
                status=UpsertStatus.NOOP,
                entity_id=None,
                reason=str(result.error),
            )
        entity_dict = result.value
        entity_id = UUID(entity_dict["id"])
        await record_create(
            self._change_log,
            user_id=UUID(user_id),
            entity_type=entity_type,
            entity_id=entity_id,
            new_value=entity_dict,
            source=source,
            reason="upsert: new entity",
            agent_run_id=agent_run_id,
        )
        # `derived_from_*` evidence relations are materialised as graph
        # edges by coherence_v2._materialise_edges (called from the graph
        # mirror below) — the legacy `evidences` table is gone.
        # Merge the persisted entity (vertex props) with the original
        # coherence payload (relation keys like linked_skill_ids /
        # related_project_id / derived_from_* — these are no longer SQL
        # columns after migration 0017 and only survive in the input).
        graph_payload = {**payload, **entity_dict}
        await self._mirror_entity_to_graph(
            entity_type=entity_type,
            user_id=UUID(user_id),
            entity_id=entity_id,
            payload=graph_payload,
            source=source,
            chat_session_id=chat_session_id,
        )
        return UpsertOutcome(status=UpsertStatus.CREATED, entity_id=entity_id)

    async def _merge(
        self,
        *,
        entity_type: str,
        user_id: str,
        existing_id: UUID,
        payload: dict[str, Any],
        config: dict[str, Any],
        source: str,
        uow: UnitOfWork,
        agent_run_id: str | None,
        chat_session_id: str | None = None,
        match: MatchResult | None = None,
    ) -> UpsertOutcome:
        # Audit basis: WHY did we merge (exact name vs semantic similarity)?
        basis = ""
        if match is not None:
            basis = f" [{match.kind.value}"
            if match.score is not None:
                basis += f" {match.score:.2f}"
            basis += "]"
        repo = config["repo"](self._session)
        existing = await repo.get(UUID(user_id), existing_id)
        if existing is None:
            # The exact/semantic match disappeared between lookup and merge.
            # Re-create instead of crashing.
            return await self._create(
                entity_type=entity_type,
                user_id=user_id,
                payload=payload,
                config=config,
                source=source,
                uow=uow,
                agent_run_id=agent_run_id,
                chat_session_id=chat_session_id,
            )

        existing_dict = _serialize(existing)
        plan = merge_for(entity_type, existing_dict, _strip_metadata_keys(payload))

        if plan.needs_user_confirmation:
            sugg_id = await self._emit_suggestion(
                user_id=user_id,
                entity_type=entity_type,
                candidates=[existing_id],
                payload=payload,
                kind=plan.suggestion_kind or "merge_review",
            )
            return UpsertOutcome(
                status=UpsertStatus.SUGGESTED,
                entity_id=existing_id,
                diffs=plan.diffs,
                suggestion_id=sugg_id,
            )

        if not plan.diffs:
            # Nothing changed on the entity itself, but the user may be
            # confirming a new relation (e.g. "I used Python in project X").
            # Re-run the graph mirror so any derived_from_* / linked_*
            # edges still materialise (idempotent).
            await self._mirror_entity_to_graph(
                entity_type=entity_type,
                user_id=UUID(user_id),
                entity_id=existing_id,
                payload={**payload, **existing_dict},
                source=source,
                chat_session_id=chat_session_id,
            )
            return UpsertOutcome(status=UpsertStatus.NOOP, entity_id=existing_id, reason="no-op")

        # Apply changes through the existing CRUD path (preserves event emission
        # + embedding refresh + RLS).
        crud = config["crud"](repo, self._scheduler)
        update_payload = {k: v for k, v in plan.merged_payload.items() if k != "id"}
        # `id` and timestamps are managed by the repo; drop anything that
        # collides with computed fields.
        update_payload = _strip_metadata_keys(update_payload)
        result = await crud.update(
            user_id=user_id,
            entity_id=str(existing_id),
            patch=update_payload,
            uow=uow,
        )
        if result.is_failure:
            return UpsertOutcome(
                status=UpsertStatus.NOOP,
                entity_id=existing_id,
                reason=str(result.error),
            )
        await record_merge(
            self._change_log,
            user_id=UUID(user_id),
            entity_type=entity_type,
            entity_id=existing_id,
            diffs=plan.diffs,
            source=source,
            reason=f"upsert: merged via rules{basis}",
            agent_run_id=agent_run_id,
        )
        graph_payload = {**payload, **plan.merged_payload}
        await self._mirror_entity_to_graph(
            entity_type=entity_type,
            user_id=UUID(user_id),
            entity_id=existing_id,
            payload=graph_payload,
            source=source,
            chat_session_id=chat_session_id,
        )
        return UpsertOutcome(
            status=UpsertStatus.MERGED,
            entity_id=existing_id,
            diffs=plan.diffs,
            reason=f"merged{basis}",
        )

    async def _mirror_entity_to_graph(
        self,
        *,
        entity_type: str,
        user_id: UUID,
        entity_id: UUID,
        payload: dict[str, Any],
        source: str,
        chat_session_id: str | None = None,
    ) -> None:
        """Sprint M dual-write + Sprint N graph-aware side-effects.

        Best-effort: graph failures must not break the legacy SQL write path
        (the user's data still lives in the relational tables). The graph
        becomes authoritative for relations in Sprint R; until then it acts
        as an index that Sprint N+ retrieval reads from.

        Steps:
          1. Upsert the personal :Entity vertex (Sprint M).
          2. Coherence v2 post-upsert: ESCO linking, edge materialisation,
             quarantine handling (Sprint N).
        """
        try:
            confidence = payload.get("confidence")
            await universe_graph_service.upsert_entity(
                self._session,
                entity_id=entity_id,
                user_id=user_id,
                kind=entity_type,
                confidence=float(confidence) if confidence is not None else None,
                source=source,
            )
        except Exception as exc:
            _log.warning(
                "graph_mirror_failed",
                entity_type=entity_type,
                entity_id=str(entity_id),
                error=str(exc),
            )
            return

        # Sprint N: ontology linking + edge materialisation + outlier flag.
        try:
            from src.coherence.application.coherence_v2 import post_upsert

            await post_upsert(
                self._session,
                entity_type=entity_type,
                user_id=user_id,
                entity_id=entity_id,
                payload=payload,
                source=source,
            )
        except Exception as exc:
            _log.warning(
                "coherence_v2_post_upsert_failed",
                entity_type=entity_type,
                entity_id=str(entity_id),
                error=str(exc),
            )

        # Sprint P: link the entity to its episode (chat session).
        if chat_session_id:
            try:
                from src.graph.application.episodes import record_touch

                await record_touch(
                    self._session,
                    user_id=user_id,
                    chat_session_id=chat_session_id,
                    entity_id=entity_id,
                )
            except Exception as exc:
                _log.warning(
                    "episode_touch_failed",
                    entity_id=str(entity_id),
                    chat_session_id=chat_session_id,
                    error=str(exc),
                )

    async def _emit_suggestion(
        self,
        *,
        user_id: str,
        entity_type: str,
        candidates: list[UUID],
        payload: dict[str, Any],
        kind: str = "merge_candidates",
    ) -> UUID:
        sid = uuid4()
        await self._session.execute(
            text(
                """
                INSERT INTO suggestions (
                    id, user_id, kind, title, body, payload, source, status, priority, created_at
                ) VALUES (
                    :id, :uid, :kind, :title, NULL,
                    CAST(:payload AS jsonb),
                    'coherence', 'pending', 50, now()
                )
                """
            ),
            {
                "id": str(sid),
                "uid": user_id,
                "kind": kind,
                "title": f"Confirma cómo tratar este {entity_type}",
                "payload": _to_json(
                    {
                        "entity_type": entity_type,
                        "candidates": [str(c) for c in candidates],
                        "payload": payload,
                    }
                ),
            },
        )
        return sid


_NEVER_PATCH = {
    "id",
    "user_id",
    "created_at",
    "updated_at",
    "deleted_at",
    "last_reviewed_at",
    "embedding",
    "_events",
    # Relation keys — dropped as SQL columns in migration 0017; they now
    # flow only to the graph layer (coherence_v2._materialise_edges) and
    # must never reach the SQL CRUD / entity constructor.
    "evidence_refs",
    "linked_skill_ids",
    "linked_project_id",
    "related_project_id",
    "superseded_by",
}


def _strip_metadata_keys(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove keys the engine never patches:
       - coherence-only `derived_from_*` / `mentioned_in_*`
       - timestamps / system fields managed by the repo layer
    """
    return {
        k: v
        for k, v in payload.items()
        if not k.startswith("derived_from_")
        and k not in _NEVER_PATCH
        and k != "mentioned_in_note_id"
    }


def _to_json(v: Any) -> str:
    import json

    return json.dumps(v, default=str)
