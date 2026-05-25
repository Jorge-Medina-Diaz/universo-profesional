"""Coherence v2 — graph-aware upsert orchestration.

Sprint N adds three behaviours on top of the Sprint G dual-write hook:

  • **ESCO entity linking** — kinds with `onto_link_kind != None` are
    routed through the linker. A LINKED result gets a :LINKS_TO_ESCO
    edge; a SUGGESTED result lands in `entity_quarantine` for the chat
    coordinator to resolve via HITL. Cross-type dedup falls out for free
    once two personal nodes point at the same ESCO IRI.

  • **Edge materialisation** — `derived_from_project_id`,
    `linked_skill_ids`, `related_project_id`, `superseded_by` and the
    artifact links land as typed AGE edges. The legacy `evidences` table
    still receives the polymorphic row until Sprint R cutover, so the
    graph and SQL stay in sync.

  • **Outlier flag (best-effort)** — Sprint P moves this into the
    curator workflow; for now we only expose `flag_outliers_for_user()`
    so tests and the cli can trigger it explicitly.

Everything in this module is *additive* — a failure here logs and
returns rather than rolling back the legacy SQL write. The graph is an
overlay during the Sprint N→Q migration window.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.application.esco_linker import (
    EscoCandidate,
    LinkState,
    esco_linker,
)
from src.graph.application.outlier_detection import (
    detect_outliers,
    mark_outlier,
)
from src.graph.application.retrieval import invalidate_snapshot
from src.graph.application.universe_graph import universe_graph_service
from src.graph.domain import schema
from src.graph.domain.registry import GRAPH_REGISTRY, GraphNodeKind
from src.graph.infrastructure.age_client import cypher

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Per-entity hook — called by the dual-write path in upsert_use_cases.
# ---------------------------------------------------------------------------


async def post_upsert(
    session: AsyncSession,
    *,
    entity_type: str,
    user_id: UUID,
    entity_id: UUID,
    payload: dict[str, Any],
    source: str,
) -> None:
    """Run all graph-aware side-effects of an upsert.

    Order:
      1. ESCO link (skills, experiences) — best-effort.
      2. Edge materialisation from derived_from_* / linked_* / related_*.
      3. Outlier detection — deferred to the curator workflow, no-op here.
    """
    cfg = GRAPH_REGISTRY.get(entity_type)
    if cfg is None:
        return

    # 1. ESCO linking — wrapped in a SAVEPOINT so a failure in the
    #    embedding/pgvector call (network, timeout) rolls back only the
    #    linking attempt, never the outer upsert transaction.
    if cfg.onto_link_kind is not None:
        try:
            async with session.begin_nested():
                await _link_to_esco(
                    session,
                    user_id=user_id,
                    entity_id=entity_id,
                    kind=entity_type,
                    payload=payload,
                    cfg=cfg,
                )
        except Exception as exc:
            logger.warning("esco_link_failed", entity_id=str(entity_id), error=str(exc))

    # 2. Edge materialisation
    try:
        await _materialise_edges(
            session,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            source=source,
        )
    except Exception as exc:
        logger.warning(
            "edge_materialisation_failed", entity_id=str(entity_id), error=str(exc)
        )

    # 2b. Agentic enrichment (additive, best-effort) — infer structural edges
    #     from the freshly-captured payload (tech_stack/competences → skills).
    #     Wrapped so an inference failure never rolls back the upsert.
    try:
        from src.universe.application.enrichment import infer_for_entity

        async with session.begin_nested():
            await infer_for_entity(
                session,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                payload=payload,
            )
    except Exception as exc:
        logger.warning("enrichment_infer_failed", entity_id=str(entity_id), error=str(exc))

    # 3. Invalidate the PPR snapshot — next retrieve rebuilds with the
    #    new vertex/edges in place. Cheap.
    await invalidate_snapshot(user_id)


# ---------------------------------------------------------------------------
# ESCO linking
# ---------------------------------------------------------------------------


async def _link_to_esco(
    session: AsyncSession,
    *,
    user_id: UUID,
    entity_id: UUID,
    kind: str,
    payload: dict[str, Any],
    cfg: GraphNodeKind,
) -> None:
    text_in = cfg.embedding_text(payload)
    if not text_in:
        return
    assert cfg.onto_link_kind is not None
    result = await esco_linker.link(
        session, text_in, kind=cfg.onto_link_kind
    )

    if result.state == LinkState.LINKED:
        await _attach_esco_edge(
            session,
            user_id=user_id,
            entity_id=entity_id,
            esco_uri=result.esco_uri,
            target_label="EscoSkill" if cfg.onto_link_kind == "skill" else "Occupation",
            score=result.score or 0.0,
        )
    elif result.state == LinkState.SUGGESTED:
        await _open_esco_quarantine(
            session,
            user_id=user_id,
            entity_id=entity_id,
            kind=kind,
            candidates=result.candidates,
            score=result.score or 0.0,
        )
    # ORPHAN / ERROR — no action; the user may volunteer the right concept
    # via chat later, or the linker may succeed once the user adds more
    # context to the entity.


async def _attach_esco_edge(
    session: AsyncSession,
    *,
    user_id: UUID,
    entity_id: UUID,
    esco_uri: str | None,
    target_label: str,
    score: float,
) -> None:
    if not esco_uri:
        return
    # Stash the URI on the personal Entity node for fast lookup, in
    # addition to the edge — the chat coordinator reads it in some flows.
    await cypher(
        session,
        schema.GRAPH_PERSONAL,
        """
        MATCH (e:Entity {id: $eid, user_id: $uid})
        SET e.esco_uri = $uri
        """,
        params={"eid": str(entity_id), "uid": str(user_id), "uri": esco_uri},
    )
    # The :LINKS_TO_ESCO edge crosses graph boundaries (personal →
    # ontology). AGE does not allow cross-graph edges, so we persist the
    # link as a row in `graph_esco_links` (created by migration 0016).
    await session.execute(
        text(
            """
            INSERT INTO graph_esco_links
                (user_id, entity_id, esco_uri, target_label, score)
            VALUES (:uid, :eid, :uri, :tgt, :score)
            ON CONFLICT (user_id, entity_id, esco_uri) DO UPDATE
              SET score = EXCLUDED.score,
                  target_label = EXCLUDED.target_label
            """
        ),
        {
            "uid": str(user_id),
            "eid": str(entity_id),
            "uri": esco_uri,
            "tgt": target_label,
            "score": round(score, 3),
        },
    )


async def _open_esco_quarantine(
    session: AsyncSession,
    *,
    user_id: UUID,
    entity_id: UUID,
    kind: str,
    candidates: list[EscoCandidate],
    score: float,
) -> None:
    """Insert a SUGGESTED row into entity_quarantine (idempotent)."""
    payload = json.dumps(
        [
            {
                "uri": c.uri,
                "label": c.label,
                "pref_label_es": c.pref_label_es,
                "pref_label_en": c.pref_label_en,
                "score": round(c.score, 3),
            }
            for c in candidates
        ]
    )
    await session.execute(
        text(
            """
            INSERT INTO entity_quarantine
                (user_id, entity_id, kind, reason, candidates, notes)
            SELECT :uid, :eid, :kind, 'esco_low_confidence',
                   CAST(:cands AS jsonb), :notes
            WHERE NOT EXISTS (
                SELECT 1 FROM entity_quarantine
                 WHERE user_id = :uid
                   AND entity_id = :eid
                   AND reason = 'esco_low_confidence'
                   AND resolved_at IS NULL
            )
            """
        ),
        {
            "uid": str(user_id),
            "eid": str(entity_id),
            "kind": kind,
            "cands": payload,
            "notes": f"top_score={score:.3f}",
        },
    )


# ---------------------------------------------------------------------------
# Edge materialisation
# ---------------------------------------------------------------------------


# Map of "payload key → (edge_type, target_kind)" used to materialise the
# legacy `derived_from_*` semantics as typed graph edges.
_DERIVED_FROM_EDGES: dict[str, tuple[str, str]] = {
    "derived_from_project_id": (schema.DERIVED_FROM, "project"),
    "derived_from_experience_id": (schema.DERIVED_FROM, "experience"),
    "derived_from_course_id": (schema.DERIVED_FROM, "course"),
    "derived_from_certification_id": (schema.DERIVED_FROM, "certification"),
    "derived_from_achievement_id": (schema.DERIVED_FROM, "achievement"),
    "derived_from_artifact_id": (schema.DERIVED_FROM, "artifact"),
}


async def _materialise_edges(
    session: AsyncSession,
    *,
    user_id: UUID,
    entity_type: str,
    entity_id: UUID,
    payload: dict[str, Any],
    source: str,
) -> None:
    """Translate legacy payload shorthand into typed graph edges."""

    # `derived_from_*` keys (used by skills + artifacts) → DERIVED_FROM
    for key, (edge_type, _target_kind) in _DERIVED_FROM_EDGES.items():
        target_id = payload.get(key)
        if not target_id:
            continue
        try:
            tgt_uuid = UUID(str(target_id))
        except ValueError:
            continue
        await universe_graph_service.upsert_edge(
            session,
            edge_type=edge_type,
            source_id=entity_id,
            target_id=tgt_uuid,
            user_id=user_id,
            source=source,
        )

    # Artifact-specific links
    if entity_type == "artifact":
        for skill_id in payload.get("linked_skill_ids", []) or []:
            try:
                sid = UUID(str(skill_id))
            except ValueError:
                continue
            await universe_graph_service.upsert_edge(
                session,
                edge_type=schema.USES_TECH,
                source_id=entity_id,
                target_id=sid,
                user_id=user_id,
                source=source,
            )
        proj_id = payload.get("linked_project_id")
        if proj_id:
            try:
                pid = UUID(str(proj_id))
                await universe_graph_service.upsert_edge(
                    session,
                    edge_type=schema.PART_OF,
                    source_id=entity_id,
                    target_id=pid,
                    user_id=user_id,
                    source=source,
                )
            except ValueError:
                pass

    # Architecture decision links
    if entity_type == "architecture_decision":
        rel_proj = payload.get("related_project_id")
        if rel_proj:
            try:
                await universe_graph_service.upsert_edge(
                    session,
                    edge_type=schema.PART_OF,
                    source_id=entity_id,
                    target_id=UUID(str(rel_proj)),
                    user_id=user_id,
                    source=source,
                )
            except ValueError:
                pass
        superseded_by = payload.get("superseded_by")
        if superseded_by:
            try:
                # The *new* ADR supersedes *this* one — edge points from
                # superseder to superseded (matches SUPERSEDES verb).
                await universe_graph_service.upsert_edge(
                    session,
                    edge_type=schema.SUPERSEDES,
                    source_id=UUID(str(superseded_by)),
                    target_id=entity_id,
                    user_id=user_id,
                    source=source,
                )
            except ValueError:
                pass


# ---------------------------------------------------------------------------
# Outlier sweep (one-shot, used by the curator + manual cli)
# ---------------------------------------------------------------------------


async def flag_outliers_for_user(
    session: AsyncSession,
    user_id: UUID,
) -> int:
    """Run outlier detection and write quarantine rows. Returns count."""
    results = await detect_outliers(session, user_id)
    flagged = 0
    for r in results:
        if not r.is_outlier:
            continue
        await mark_outlier(
            session,
            user_id=user_id,
            entity_id=r.entity_id,
            kind=r.kind,
            iso_score=r.iso_forest_score,
            lof_score=r.lof_score,
        )
        flagged += 1
    return flagged


# ---------------------------------------------------------------------------
# Quarantine resolution (called by the HITL handler in Sprint N.5)
# ---------------------------------------------------------------------------


async def resolve_quarantine(
    session: AsyncSession,
    *,
    quarantine_id: UUID,
    user_id: UUID,
    chosen_uri: str | None,
    resolution: str,
) -> None:
    """Mark a quarantine row resolved. If `chosen_uri` is provided, also
    attach the corresponding ESCO link to the entity.
    """
    row = (
        await session.execute(
            text(
                """
                SELECT entity_id::text AS entity_id,
                       kind,
                       candidates
                FROM entity_quarantine
                WHERE id = :qid AND user_id = :uid
                """
            ),
            {"qid": str(quarantine_id), "uid": str(user_id)},
        )
    ).first()
    if row is None:
        return

    if chosen_uri:
        # Find the candidate's target_label from the stored candidates.
        target_label = "EscoSkill"
        for cand in row.candidates or []:
            if cand.get("uri") == chosen_uri:
                target_label = cand.get("label", target_label)
                break
        await _attach_esco_edge(
            session,
            user_id=user_id,
            entity_id=UUID(row.entity_id),
            esco_uri=chosen_uri,
            target_label=target_label,
            score=1.0,
        )

    await session.execute(
        text(
            """
            UPDATE entity_quarantine
               SET resolved_at = now(),
                   resolution = :resolution
             WHERE id = :qid AND user_id = :uid
            """
        ),
        {"qid": str(quarantine_id), "uid": str(user_id), "resolution": resolution},
    )


# ---------------------------------------------------------------------------
# Cross-type dedup helper — call before creating a personal node.
# ---------------------------------------------------------------------------


async def find_by_esco_uri(
    session: AsyncSession,
    *,
    user_id: UUID,
    esco_uri: str,
    kinds: Iterable[str] | None = None,
) -> UUID | None:
    """Return an existing personal entity id for this user that already
    links to the given ESCO concept. Used by coherence_v2's "prefer
    ontology over per-table dedup" rule, which is what eliminates
    duplicates like "AWS Lambda" / "Lambda (AWS)" — both link to the
    same `esco_uri`, so the second upsert merges into the first.
    """
    kinds_filter = ""
    params: dict[str, Any] = {"uid": str(user_id), "uri": esco_uri}
    if kinds:
        # Comma-separated list of validated identifiers; safe to interpolate.
        joined = ",".join(f"'{k}'" for k in kinds if k.isidentifier())
        if joined:
            kinds_filter = f" AND kind IN ({joined})"

    row = (
        await session.execute(
            text(
                f"""
                SELECT entity_id::text AS entity_id
                FROM graph_esco_links gel
                WHERE gel.user_id = :uid
                  AND gel.esco_uri = :uri
                {kinds_filter}
                ORDER BY score DESC
                LIMIT 1
                """
            ),
            params,
        )
    ).first()
    return UUID(row.entity_id) if row else None
