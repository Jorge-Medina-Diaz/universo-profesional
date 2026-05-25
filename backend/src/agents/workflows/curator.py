"""Curator v2 — graph-aware daily sweep over the universe.

Runs daily per active user. Mutates only the safe surfaces (orphan
evidences, confidence decay); everything user-impacting (merge
candidates, archive suggestions, outlier flags) is filed as a
`suggestions` row or an `entity_quarantine` row for HITL resolution.

Sprint P rewrite: the curator now drives off `GRAPH_REGISTRY` (single
source of truth, no parallel whitelist) and also runs the Sprint N
outlier sweep + checks for graph-shaped problems:

  • Duplicates within a kind (existing dense similarity ≥ 0.94 → merge
    suggestion). Skips kinds whose table has no embedding column.
  • Confidence decay on entries unreviewed in > 365 days.
  • Outlier flags (IsoForest + LOF ensemble).
  • Orphan graph vertices — :Entity nodes whose backing SQL row has been
    hard-deleted (e.g. a manual delete during data migration) are
    DETACH DELETE-d from the AGE personal graph. (The legacy `evidences`
    SQL table was dropped in the Sprint R cutover; relations now live in
    the graph.)

Every sweep runs inside its own SAVEPOINT and the per-user batch loop is
fault-isolated, so a single failure never aborts the whole nightly run.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.domain import schema
from src.graph.domain.registry import GRAPH_REGISTRY
from src.graph.infrastructure.age_client import cypher, parse_agtype
from src.shared.db import get_session_factory, set_rls_user

logger = structlog.get_logger(__name__)


# Cache of table → has-embedding-column for the process lifetime (schema
# only changes via migrations, which restart the workers). Some kinds
# (e.g. artifacts) have no embedding column and must be skipped by the
# similarity-based duplicate detector.
_EMBEDDING_TABLE_CACHE: dict[str, bool] = {}


async def _table_has_embedding(session: AsyncSession, table: str) -> bool:
    cached = _EMBEDDING_TABLE_CACHE.get(table)
    if cached is not None:
        return cached
    row = (
        await session.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = :t AND column_name = 'embedding'"
            ),
            {"t": table},
        )
    ).first()
    exists = row is not None
    _EMBEDDING_TABLE_CACHE[table] = exists
    return exists


# Curator's view of "what to scan" is the GRAPH_REGISTRY — single source
# of truth, no parallel maintenance. The exported names keep their old
# shape so older callers (cron config, tests) don't break during the
# Sprint Q→R window.
SCAN_ENTITIES: list[str] = [
    kind
    for kind, cfg in GRAPH_REGISTRY.items()
    if cfg.supports_stale
]
TABLE_BY_ENTITY: dict[str, str] = {
    kind: cfg.sql_table for kind, cfg in GRAPH_REGISTRY.items()
}
DUP_SIMILARITY_THRESHOLD = 0.94


async def _detect_duplicates(
    session: AsyncSession, *, user_id: str, entity_type: str
) -> list[tuple[str, str, float]]:
    """Cluster entries by embedding cosine similarity. Returns pairs above threshold."""
    table = TABLE_BY_ENTITY[entity_type]
    # Self-join via embedding; only keep one direction (id_a < id_b) to dedupe pairs.
    rows = (
        await session.execute(
            text(
                f"""
                SELECT a.id::text AS id_a, b.id::text AS id_b,
                       1 - (a.embedding <=> b.embedding) AS score
                FROM {table} a
                JOIN {table} b ON a.user_id = b.user_id AND a.id < b.id
                WHERE a.user_id = :uid
                  AND a.embedding IS NOT NULL
                  AND b.embedding IS NOT NULL
                  AND 1 - (a.embedding <=> b.embedding) >= :th
                ORDER BY score DESC LIMIT 20
                """  # noqa: S608 — table comes from closed-set
            ),
            {"uid": user_id, "th": DUP_SIMILARITY_THRESHOLD},
        )
    ).all()
    return [(r.id_a, r.id_b, float(r.score)) for r in rows]


async def _open_merge_suggestion(
    session: AsyncSession,
    *,
    user_id: str,
    entity_type: str,
    pair: tuple[str, str, float],
) -> None:
    sid = uuid4()
    a, b, score = pair
    payload = json.dumps(
        {"entity_type": entity_type, "candidates": [a, b], "similarity": score}
    )
    # Avoid spamming the user — skip if a pending suggestion already exists
    # for the same pair.
    existing = (
        await session.execute(
            text(
                """
                SELECT id FROM suggestions
                WHERE user_id = :uid
                  AND kind = 'merge_candidates'
                  AND status = 'pending'
                  AND payload @> CAST(:probe AS jsonb)
                LIMIT 1
                """
            ),
            {
                "uid": user_id,
                "probe": json.dumps({"entity_type": entity_type, "candidates": [a, b]}),
            },
        )
    ).first()
    if existing is not None:
        return
    await session.execute(
        text(
            """
            INSERT INTO suggestions
                (id, user_id, kind, title, body, payload, source, status, priority, created_at)
            VALUES
                (:id, :uid, 'merge_candidates', :title, NULL, CAST(:p AS jsonb),
                 'curator', 'pending', 70, now())
            """
        ),
        {
            "id": str(sid),
            "uid": user_id,
            "title": f"Posibles duplicados detectados ({entity_type})",
            "p": payload,
        },
    )


async def _clean_orphan_graph_vertices(session: AsyncSession, *, user_id: str) -> int:
    """Invalidate (not delete) :Entity vertices whose backing SQL row is gone.

    Bi-temporal principle (Graphiti/Zep): we *invalidate* — set `valid_to`
    on the vertex and its incident edges — instead of `DETACH DELETE`, so
    the node drops out of retrieval/PPR (which filter `valid_to IS NULL`)
    while history stays queryable. The only orphan scenario left is a graph
    vertex whose SQL row was hard-deleted (e.g. a manual data migration).
    """
    from src.graph.application.universe_graph import universe_graph_service
    graph_rows = await cypher(
        session,
        schema.GRAPH_PERSONAL,
        "MATCH (e:Entity {user_id: $uid}) RETURN e.id AS id, e.kind AS kind",
        params={"uid": user_id},
        column_defs="id agtype, kind agtype",
    )
    graph_ids_by_kind: dict[str, set[str]] = {}
    for row in graph_rows:
        gid = parse_agtype(row.get("id"))
        gkind = parse_agtype(row.get("kind"))
        if isinstance(gid, str) and isinstance(gkind, str):
            graph_ids_by_kind.setdefault(gkind, set()).add(gid)
    if not graph_ids_by_kind:
        return 0

    invalidated = 0
    for kind, graph_ids in graph_ids_by_kind.items():
        table = TABLE_BY_ENTITY.get(kind)
        if table is None:
            continue
        sql_rows = (
            await session.execute(
                text(
                    f"SELECT id::text AS id FROM {table} WHERE user_id = :uid"  # noqa: S608
                ),
                {"uid": user_id},
            )
        ).all()
        sql_ids = {r.id for r in sql_rows}
        for orphan_id in graph_ids - sql_ids:
            # Invalidate (valid_to=now) the vertex + its incident edges,
            # instead of hard-deleting — preserves history, drops from reads.
            await universe_graph_service.soft_delete_entity(
                session, entity_id=UUID(orphan_id), user_id=UUID(user_id)
            )
            invalidated += 1
    return invalidated


async def _decay_unreviewed(session: AsyncSession, *, user_id: str) -> int:
    """Lower confidence on entries unreviewed in > 365 days."""
    touched = 0
    for tbl in TABLE_BY_ENTITY.values():
        result = await session.execute(
            text(
                f"""
                UPDATE {tbl}
                SET confidence = GREATEST(confidence * 0.9, 0.3),
                    updated_at = now()
                WHERE user_id = :uid
                  AND (last_reviewed_at IS NULL OR last_reviewed_at < now() - INTERVAL '365 days')
                  AND COALESCE(confidence, 1.0) > 0.3
                RETURNING id
                """  # noqa: S608
            ),
            {"uid": user_id},
        )
        touched += len(result.fetchall())
    return touched


async def run_curator_for_user(*, user_id: str) -> dict[str, Any]:
    """Single-user sweep. Returns a summary dict (logged + returned for tests).

    Sprint P additions:
      • outliers_flagged — IsoForest+LOF agreement runs and writes
        entity_quarantine rows.
    """
    factory = get_session_factory()
    summary: dict[str, Any] = {
        "user_id": user_id,
        "merge_suggestions_opened": 0,
        "orphans_cleaned": 0,
        "confidence_decayed": 0,
        "outliers_flagged": 0,
        "edges_inferred": 0,
        "communities": 0,
    }
    async with factory() as session:
        await set_rls_user(session, UUID(user_id))

        # Each sweep runs inside its own SAVEPOINT so a failure (e.g. a
        # transient DB error) rolls back only that sweep and leaves the
        # outer transaction usable for the rest — one bad sweep must not
        # poison the others.

        # Duplicate detection — only kinds whose table has an embedding
        # column (artifacts dedup by exact name only, no vector).
        for entity_type in SCAN_ENTITIES:
            table = TABLE_BY_ENTITY.get(entity_type)
            if table is None or not await _table_has_embedding(session, table):
                continue
            try:
                async with session.begin_nested():
                    pairs = await _detect_duplicates(
                        session, user_id=user_id, entity_type=entity_type
                    )
                    for pair in pairs:
                        await _open_merge_suggestion(
                            session,
                            user_id=user_id,
                            entity_type=entity_type,
                            pair=pair,
                        )
                        summary["merge_suggestions_opened"] += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "curator_dup_sweep_failed",
                    user_id=user_id,
                    kind=entity_type,
                    error=str(exc),
                )

        try:
            async with session.begin_nested():
                summary["orphans_cleaned"] = await _clean_orphan_graph_vertices(
                    session, user_id=user_id
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "curator_orphan_sweep_failed", user_id=user_id, error=str(exc)
            )

        try:
            async with session.begin_nested():
                summary["confidence_decayed"] = await _decay_unreviewed(
                    session, user_id=user_id
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "curator_decay_failed", user_id=user_id, error=str(exc)
            )

        # Sleep-time enrichment: re-infer relationships + recompute career
        # pillars so the universe stays connected & clustered as it grows,
        # without the user having to trigger "Conectar" manually. (cognee
        # memify / Letta sleep-time pattern.)
        try:
            async with session.begin_nested():
                from src.universe.application.enrichment import enrich_user_graph

                stats = await enrich_user_graph(session, UUID(user_id))
                summary["edges_inferred"] = (
                    stats.related_to + stats.uses_tech + stats.part_of
                )
                summary["communities"] = stats.communities
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "curator_enrich_failed", user_id=user_id, error=str(exc)
            )

        # Sprint P: outlier sweep. Import lazily to avoid coupling curator
        # imports to scikit-learn/pyod when those packages aren't needed
        # (e.g. tests that monkeypatch the duplicates detector).
        try:
            async with session.begin_nested():
                from src.coherence.application.coherence_v2 import (
                    flag_outliers_for_user,
                )

                summary["outliers_flagged"] = await flag_outliers_for_user(
                    session, UUID(user_id)
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "curator_outlier_sweep_failed", user_id=user_id, error=str(exc)
            )

        await session.commit()
    logger.info("curator_run", **summary)
    return summary


async def curator_task(ctx: dict[str, Any], *, user_id: str) -> None:
    """Arq task entry point — called by the daily cron with the user id."""
    await run_curator_for_user(user_id=user_id)


async def _active_user_ids() -> list[str]:
    """User ids with universe activity in the last 30 days."""
    factory = get_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT DISTINCT user_id::text AS uid
                    FROM universe_change_log
                    WHERE changed_at > now() - INTERVAL '30 days'
                    """
                )
            )
        ).all()
    return [r.uid for r in rows]


async def run_curator_for_all_active_users() -> dict[str, Any]:
    """Scan users with activity in the last 30 days and run the curator on each.

    Kept for the CLI / manual runs. The nightly cron uses `curator_cron`,
    which fans the work out into per-user jobs instead of one long sweep.
    """
    out: dict[str, Any] = {
        "users_processed": 0,
        "users_failed": 0,
        "totals": {
            "merge_suggestions": 0,
            "orphans": 0,
            "decayed": 0,
            "outliers": 0,
        },
    }
    active_users = await _active_user_ids()
    for uid in active_users:
        # A single user's sweep failing must NOT abort the whole batch —
        # log it and keep going so every other user still gets curated.
        try:
            s = await run_curator_for_user(user_id=uid)
        except Exception as exc:  # noqa: BLE001
            logger.error("curator_user_failed", user_id=uid, error=str(exc))
            out["users_failed"] += 1
            continue
        out["users_processed"] += 1
        out["totals"]["merge_suggestions"] += s["merge_suggestions_opened"]
        out["totals"]["orphans"] += s["orphans_cleaned"]
        out["totals"]["decayed"] += s["confidence_decayed"]
        out["totals"]["outliers"] += s.get("outliers_flagged", 0)
    return out


async def curator_cron(ctx: dict[str, Any]) -> None:
    """Arq cron entry — fans the sweep out into per-user jobs.

    Enqueuing one bounded `curator_task` per active user (instead of one
    long inline sweep) means: a slow/failing user can't starve the rest,
    each job stays well under `job_timeout`, and the worker pool processes
    them in parallel. Falls back to an inline sweep if the redis pool is
    not on the context (e.g. a manual invocation).
    """
    user_ids = await _active_user_ids()
    redis = ctx.get("redis")
    if redis is None:
        await run_curator_for_all_active_users()
        return
    enqueued = 0
    for uid in user_ids:
        try:
            await redis.enqueue_job("curator_task", user_id=uid)
            enqueued += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("curator_enqueue_failed", user_id=uid, error=str(exc))
    logger.info("curator_cron_dispatched", users=len(user_ids), enqueued=enqueued)
