"""Outbox projections (R4 slice 1): durable, cursor-driven read-model projection
over the `domain_events` outbox.

Today the embeddings sidecar is at-most-once (fire-and-forget arq enqueue at
write time); if that enqueue/job is lost the vector silently goes stale. This
projection is the RELIABILITY NET: it cursor-scans entry_added/entry_updated
events and re-embeds, so a lost embed is repaired within a tick. It NEVER
replays the whole history (first run fast-forwards the cursor to the current
head) and per-row failures are loud dead-letters, never silent.

Slice 1 = embeddings only (idempotent, non-corrupting). Snapshot/AGE projections
(slices 2-3) build on the same substrate; deferred by design.
"""
from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.db import get_session_factory, set_rls_user

logger = structlog.get_logger(__name__)

_BATCH = 500


async def _get_cursor(session: AsyncSession, name: str) -> int | None:
    row = (
        await session.execute(
            text(
                "SELECT last_event_seq FROM outbox_projection_cursor "
                "WHERE projection_name = :n"
            ),
            {"n": name},
        )
    ).first()
    return int(row[0]) if row else None


async def _set_cursor(session: AsyncSession, name: str, seq: int) -> None:
    await session.execute(
        text(
            "UPDATE outbox_projection_cursor SET last_event_seq = :s, updated_at = now() "
            "WHERE projection_name = :n"
        ),
        {"s": seq, "n": name},
    )


async def project_embeddings_task(ctx: dict[str, Any]) -> dict[str, Any]:
    """Re-embed entities for entry_added/entry_updated events the cursor hasn't
    seen — repairing any lost fire-and-forget embed. Idempotent overwrite."""
    from src.universe.infrastructure.tasks import refresh_embedding

    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, None)  # cross-user worker scope (bypass RLS)
        cursor = await _get_cursor(session, "embeddings")
        if cursor is None:
            logger.warning("embeddings_projection_cursor_missing")
            return {"projected": 0, "note": "cursor missing"}

        # First run: fast-forward past all history so deploying the worker does
        # NOT trigger an embedding stampede over every existing entity.
        if cursor == 0:
            head = (
                await session.execute(
                    text("SELECT COALESCE(MAX(seq), 0) FROM domain_events")
                )
            ).scalar() or 0
            if int(head) > 0:
                await _set_cursor(session, "embeddings", int(head))
                await session.commit()
                logger.info("embeddings_projection_fast_forward", to_seq=int(head))
                return {"projected": 0, "fast_forwarded_to": int(head)}
            return {"projected": 0}

        rows = (
            await session.execute(
                text(
                    "SELECT seq, payload->>'entity_type' AS et, "
                    "payload->>'entity_id_str' AS eid FROM domain_events "
                    "WHERE seq > :c AND event_type IN "
                    "('universe.entry_added', 'universe.entry_updated') "
                    "ORDER BY seq LIMIT :lim"
                ),
                {"c": cursor, "lim": _BATCH},
            )
        ).all()

    if not rows:
        return {"projected": 0}

    projected = 0
    failed = 0
    last_seq = cursor
    for seq, et, eid in rows:
        last_seq = int(seq)
        if not et or not eid:
            logger.warning("embeddings_projection_bad_row", seq=last_seq)
            failed += 1
            continue
        try:
            await refresh_embedding(ctx, entity_type=et, entity_id=eid)
            projected += 1
        except Exception as exc:  # loud dead-letter — never a silent drop
            logger.error(
                "embeddings_projection_row_failed",
                seq=last_seq,
                entity_type=et,
                entity_id=eid,
                error=str(exc),
            )
            failed += 1

    # Advance once to the last examined seq (idempotent: a crash before this
    # re-processes the batch next tick, which is a harmless re-embed).
    async with factory() as session:
        await set_rls_user(session, None)
        await _set_cursor(session, "embeddings", last_seq)
        await session.commit()

    logger.info(
        "embeddings_projection_done", projected=projected, failed=failed, cursor=last_seq
    )
    return {"projected": projected, "failed": failed, "cursor": last_seq}
