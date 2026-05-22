"""Migrate legacy relation rows/columns into the AGE personal graph.

Sprint R cutover script. Before running migration 0017 (which drops the
legacy tables/columns) we have to make sure the AGE personal graph
holds an equivalent set of typed edges. This script does exactly that,
in dry-run mode by default so the operator can review the deltas
before committing.

Translations:

  evidences row (skill ↔ entity, polymorphic)
      → (:Entity {kind:'skill'})-[:DEMONSTRATES]-(:Evidence)-
        [:OCCURRED_IN | :PRODUCED]-(:Entity)
  artifacts.linked_skill_ids[]   → (:artifact)-[:USES_TECH]->(:skill)
  artifacts.linked_project_id    → (:artifact)-[:PART_OF]->(:project)
  skills.evidence_refs[*]        → (:skill)-[:DEMONSTRATES]->(:entity)
  architecture_decisions.related_project_id
                                 → (:adr)-[:PART_OF]->(:project)
  architecture_decisions.superseded_by
                                 → (:adr_new)-[:SUPERSEDES]->(:adr_old)
  user_rubric_signals row        → (:Signal {…}) + (:Entity)-[:EVIDENCES_SIGNAL]->(:Signal)

Usage:
    python -m scripts.migrate_legacy_to_graph --dry-run            # inspect counts
    python -m scripts.migrate_legacy_to_graph --apply              # write edges
    python -m scripts.migrate_legacy_to_graph --apply --user <uid> # single user

Idempotent: every edge MERGE is `MERGE … SET COALESCE(...)` so reruns
do not duplicate edges. The script also bumps `graph_ingest_meta`
('legacy_migration_applied_at') so we can detect re-application.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text

from src.graph.application.universe_graph import universe_graph_service
from src.graph.domain import schema as gschema
from src.graph.infrastructure.age_client import cypher
from src.shared.db import (
    dispose_engine,
    get_session_factory,
    set_rls_user,
)

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class MigrationStats:
    users_processed: int = 0
    evidences_translated: int = 0
    artifact_skill_edges: int = 0
    artifact_project_edges: int = 0
    skill_evidence_refs: int = 0
    adr_project_edges: int = 0
    adr_supersedes_edges: int = 0
    signals_materialised: int = 0
    errors: list[str] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


async def _list_users(
    session: Any, only_user: UUID | None = None
) -> list[UUID]:
    """Discover every user that has any legacy data.

    Bypasses RLS for the duration of the listing — `user_rubric_signals`
    (and other legacy tables) have row-level policies keyed on the
    session-local `app.current_user_id`, which is unset in this admin
    script context. Without the bypass, the UNION returns 0 rows for
    every protected table and the script silently migrates nothing.
    """
    if only_user:
        return [only_user]
    # `SET LOCAL row_security = off` requires the session role to be
    # SUPERUSER or have BYPASSRLS. The `cvs` role used by the backend
    # container is the database owner and qualifies; if you run this
    # script with a different role, grant BYPASSRLS first.
    await session.execute(text("SET LOCAL row_security = off"))
    rows = (
        await session.execute(
            text(
                """
                SELECT DISTINCT user_id::text AS uid
                FROM (
                    SELECT user_id FROM evidences
                    UNION SELECT user_id FROM artifacts
                    UNION SELECT user_id FROM skills
                    UNION SELECT user_id FROM architecture_decisions
                    UNION SELECT user_id FROM user_rubric_signals
                ) sub
                WHERE user_id IS NOT NULL
                """
            )
        )
    ).all()
    return [UUID(r.uid) for r in rows]


async def _migrate_evidences(
    session: Any, user_id: UUID, dry_run: bool, stats: MigrationStats
) -> None:
    rows = (
        await session.execute(
            text(
                """
                SELECT id::text AS id, skill_id::text AS skill_id,
                       evidence_entity_type, evidence_entity_id::text AS target_id,
                       weight, notes, created_at
                FROM evidences
                WHERE user_id = :uid
                """
            ),
            {"uid": str(user_id)},
        )
    ).all()
    for row in rows:
        stats.evidences_translated += 1
        if dry_run:
            continue
        # Edge: (skill)-[:DEMONSTRATES]->(target)
        try:
            await universe_graph_service.upsert_edge(
                session,
                edge_type=gschema.DEMONSTRATES,
                source_id=UUID(row.skill_id),
                target_id=UUID(row.target_id),
                user_id=user_id,
                confidence=float(row.weight or 1.0),
                source="legacy_evidences",
            )
        except Exception as exc:  # noqa: BLE001
            stats.errors.append(f"evidence {row.id}: {exc}")


async def _migrate_artifact_links(
    session: Any, user_id: UUID, dry_run: bool, stats: MigrationStats
) -> None:
    rows = (
        await session.execute(
            text(
                """
                SELECT id::text AS id,
                       linked_skill_ids,
                       linked_project_id::text AS linked_project_id
                FROM artifacts
                WHERE user_id = :uid AND deleted_at IS NULL
                """
            ),
            {"uid": str(user_id)},
        )
    ).all()
    for row in rows:
        artifact_id = UUID(row.id)
        for sk_raw in row.linked_skill_ids or []:
            try:
                stats.artifact_skill_edges += 1
                if dry_run:
                    continue
                await universe_graph_service.upsert_edge(
                    session,
                    edge_type=gschema.USES_TECH,
                    source_id=artifact_id,
                    target_id=UUID(str(sk_raw)),
                    user_id=user_id,
                    source="legacy_artifact_links",
                )
            except Exception as exc:  # noqa: BLE001
                stats.errors.append(f"artifact {row.id} → skill {sk_raw}: {exc}")
        if row.linked_project_id:
            try:
                stats.artifact_project_edges += 1
                if dry_run:
                    continue
                await universe_graph_service.upsert_edge(
                    session,
                    edge_type=gschema.PART_OF,
                    source_id=artifact_id,
                    target_id=UUID(row.linked_project_id),
                    user_id=user_id,
                    source="legacy_artifact_links",
                )
            except Exception as exc:  # noqa: BLE001
                stats.errors.append(
                    f"artifact {row.id} → project {row.linked_project_id}: {exc}"
                )


async def _migrate_skill_evidence_refs(
    session: Any, user_id: UUID, dry_run: bool, stats: MigrationStats
) -> None:
    rows = (
        await session.execute(
            text(
                """
                SELECT id::text AS id, evidence_refs
                FROM skills
                WHERE user_id = :uid AND deleted_at IS NULL
                  AND evidence_refs IS NOT NULL
                  AND jsonb_array_length(COALESCE(evidence_refs, '[]'::jsonb)) > 0
                """
            ),
            {"uid": str(user_id)},
        )
    ).all()
    for row in rows:
        skill_id = UUID(row.id)
        # evidence_refs is a jsonb list of dicts {entity_type, entity_id}
        for ref in row.evidence_refs or []:
            target_id = ref.get("entity_id") if isinstance(ref, dict) else None
            if not target_id:
                continue
            try:
                stats.skill_evidence_refs += 1
                if dry_run:
                    continue
                await universe_graph_service.upsert_edge(
                    session,
                    edge_type=gschema.DEMONSTRATES,
                    source_id=skill_id,
                    target_id=UUID(str(target_id)),
                    user_id=user_id,
                    source="legacy_evidence_refs",
                )
            except Exception as exc:  # noqa: BLE001
                stats.errors.append(f"skill {row.id} ref {target_id}: {exc}")


async def _migrate_adr_fks(
    session: Any, user_id: UUID, dry_run: bool, stats: MigrationStats
) -> None:
    rows = (
        await session.execute(
            text(
                """
                SELECT id::text AS id,
                       related_project_id::text AS rel_proj,
                       superseded_by::text AS sup_by
                FROM architecture_decisions
                WHERE user_id = :uid AND deleted_at IS NULL
                """
            ),
            {"uid": str(user_id)},
        )
    ).all()
    for row in rows:
        adr_id = UUID(row.id)
        if row.rel_proj:
            stats.adr_project_edges += 1
            if not dry_run:
                try:
                    await universe_graph_service.upsert_edge(
                        session,
                        edge_type=gschema.PART_OF,
                        source_id=adr_id,
                        target_id=UUID(row.rel_proj),
                        user_id=user_id,
                        source="legacy_adr_fks",
                    )
                except Exception as exc:  # noqa: BLE001
                    stats.errors.append(
                        f"adr {row.id} → project {row.rel_proj}: {exc}"
                    )
        if row.sup_by:
            stats.adr_supersedes_edges += 1
            if not dry_run:
                try:
                    # The *new* ADR supersedes *this* one; superseder is
                    # the source, the old ADR is the target.
                    await universe_graph_service.upsert_edge(
                        session,
                        edge_type=gschema.SUPERSEDES,
                        source_id=UUID(row.sup_by),
                        target_id=adr_id,
                        user_id=user_id,
                        source="legacy_adr_fks",
                    )
                except Exception as exc:  # noqa: BLE001
                    stats.errors.append(
                        f"adr {row.id} ← supersedes {row.sup_by}: {exc}"
                    )


async def _materialise_signals(
    session: Any, user_id: UUID, dry_run: bool, stats: MigrationStats
) -> None:
    """Convert each user_rubric_signals row into a :Signal vertex.

    The :EVIDENCES_SIGNAL edge from each evidence entity to the signal
    is also materialised so retrieval can traverse from a personal
    entity to the rubric concept it backs.
    """
    rows = (
        await session.execute(
            text(
                """
                SELECT id::text AS id,
                       rubric_chunk_id::text AS chunk_id,
                       section_kind, status,
                       confidence, evidence_entity_type,
                       evidence_entity_ids,
                       notes, source, last_reviewed_at
                FROM user_rubric_signals
                WHERE user_id = :uid AND deleted_at IS NULL
                """
            ),
            {"uid": str(user_id)},
        )
    ).all()
    for row in rows:
        signal_id = UUID(row.id)
        if dry_run:
            stats.signals_materialised += 1
            continue
        # Create the :Signal node.
        try:
            await cypher(
                session,
                gschema.GRAPH_PERSONAL,
                """
                MERGE (s:Signal {id: $sid, user_id: $uid})
                SET s.rubric_chunk_id = $chunk,
                    s.section_kind = $section,
                    s.status = $status,
                    s.confidence = $conf,
                    s.notes = $notes,
                    s.source = $src,
                    s.valid_from = COALESCE(s.valid_from, $now),
                    s.updated_at = $now
                """,
                params={
                    "sid": str(signal_id),
                    "uid": str(user_id),
                    "chunk": row.chunk_id,
                    "section": row.section_kind,
                    "status": row.status,
                    "conf": float(row.confidence or 0.0),
                    "notes": row.notes,
                    "src": row.source,
                    "now": _now_iso(),
                },
            )
            stats.signals_materialised += 1
        except Exception as exc:  # noqa: BLE001
            stats.errors.append(f"signal {row.id}: {exc}")
            continue
        # Wire each evidence entity → signal.
        for ev_raw in row.evidence_entity_ids or []:
            try:
                await cypher(
                    session,
                    gschema.GRAPH_PERSONAL,
                    """
                    MATCH (e:Entity {id: $eid, user_id: $uid}),
                          (s:Signal {id: $sid, user_id: $uid})
                    MERGE (e)-[r:EVIDENCES_SIGNAL]->(s)
                    SET r.valid_from = COALESCE(r.valid_from, $now),
                        r.valid_to = NULL
                    """,
                    params={
                        "eid": str(ev_raw),
                        "uid": str(user_id),
                        "sid": str(signal_id),
                        "now": _now_iso(),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                stats.errors.append(
                    f"signal {row.id} ← evidence {ev_raw}: {exc}"
                )


async def _migrate_user(
    session: Any, user_id: UUID, dry_run: bool, stats: MigrationStats
) -> None:
    await set_rls_user(session, user_id)
    await _migrate_evidences(session, user_id, dry_run, stats)
    await _migrate_artifact_links(session, user_id, dry_run, stats)
    await _migrate_skill_evidence_refs(session, user_id, dry_run, stats)
    await _migrate_adr_fks(session, user_id, dry_run, stats)
    await _materialise_signals(session, user_id, dry_run, stats)
    stats.users_processed += 1


async def _record_completion(session: Any) -> None:
    await session.execute(
        text(
            """
            INSERT INTO graph_ingest_meta (name, value)
            VALUES ('legacy_migration_applied_at', :now)
            ON CONFLICT (name) DO UPDATE
              SET value = EXCLUDED.value, updated_at = now()
            """
        ),
        {"now": _now_iso()},
    )


async def _run(
    only_user: UUID | None, dry_run: bool
) -> MigrationStats:
    factory = get_session_factory()
    stats = MigrationStats()
    async with factory() as session:
        users = await _list_users(session, only_user)
    for uid in users:
        async with factory() as session:
            try:
                await _migrate_user(session, uid, dry_run, stats)
                if not dry_run:
                    await session.commit()
            except Exception as exc:  # noqa: BLE001
                stats.errors.append(f"user {uid}: {exc}")
    if not dry_run:
        async with factory() as session:
            await _record_completion(session)
            await session.commit()
    # Dispose the engine inside the same event loop that created it —
    # disposing from a second asyncio.run() raises "Event loop is closed".
    await dispose_engine()
    return stats


def main() -> int:
    import dataclasses

    parser = argparse.ArgumentParser(
        description="Migrate legacy relations into universe_personal graph"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Actually write edges (default: dry-run)"
    )
    parser.add_argument(
        "--user", type=str, default=None, help="Migrate just one user_id"
    )
    args = parser.parse_args()

    only_user = UUID(args.user) if args.user else None
    dry_run = not args.apply

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    stats = asyncio.run(_run(only_user, dry_run))
    # `MigrationStats` is a slots dataclass — no __dict__, use asdict().
    print(json.dumps(dataclasses.asdict(stats), indent=2, default=str))
    if stats.errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
