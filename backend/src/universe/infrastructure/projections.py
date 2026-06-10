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
    seen — repairing any lost fire-and-forget embed. Idempotent overwrite.

    The whole run holds a row lock on the cursor (`FOR UPDATE SKIP LOCKED`), so
    an overlapping cron tick — or a second worker — can't double-process or
    regress the cursor: a concurrent tick simply does nothing this minute. The
    cursor advances only to the last CONTIGUOUS success, so a transient failure
    (embedder/DB blip) is retried next tick rather than skipped forever — it is
    never a silent drop. A structurally-broken row (missing type/id, which can
    never embed) is logged loudly and stepped over so it can't stall the loop.
    """
    from src.universe.infrastructure.tasks import refresh_embedding

    factory = get_session_factory()
    projected = 0
    failed = 0
    async with factory() as session:
        await set_rls_user(session, None)  # cross-user worker scope (bypass RLS)
        # Lock the cursor row for this run. SKIP LOCKED → a concurrent tick gets
        # no row and exits cleanly instead of racing the read/advance.
        locked = (
            await session.execute(
                text(
                    "SELECT last_event_seq FROM outbox_projection_cursor "
                    "WHERE projection_name = :n FOR UPDATE SKIP LOCKED"
                ),
                {"n": "embeddings"},
            )
        ).first()
        if locked is None:
            # Distinguish "row missing" (loud) from "held by another tick" (fine).
            exists = (
                await session.execute(
                    text(
                        "SELECT 1 FROM outbox_projection_cursor WHERE projection_name = :n"
                    ),
                    {"n": "embeddings"},
                )
            ).first()
            if exists is None:
                logger.warning("embeddings_projection_cursor_missing")
                return {"projected": 0, "note": "cursor missing"}
            return {"projected": 0, "note": "locked by concurrent tick"}
        cursor = int(locked[0])

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
            await session.commit()
            return {"projected": 0}

        rows = (
            await session.execute(
                text(
                    "SELECT seq, payload->>'entity_type' AS et, "
                    "payload->>'entity_id_str' AS eid, occurred_at FROM domain_events "
                    "WHERE seq > :c AND event_type IN "
                    "('universe.entry_added', 'universe.entry_updated') "
                    "ORDER BY seq LIMIT :lim"
                ),
                {"c": cursor, "lim": _BATCH},
            )
        ).all()

        if not rows:
            await session.commit()  # release the lock
            return {"projected": 0}

        # Advance only to the last CONTIGUOUS success. `refresh_embedding` opens
        # its own session per row; the lock above serialises ticks so that is safe.
        advance_to = cursor
        for raw_seq, et, eid, event_occurred_at in rows:
            seq = int(raw_seq)
            if not et or not eid:
                # Can never embed — step over it (loud) so it doesn't wedge us.
                logger.error("embeddings_projection_bad_row", seq=seq)
                failed += 1
                advance_to = seq
                continue
            try:
                await refresh_embedding(ctx, entity_type=et, entity_id=eid)
                projected += 1
                advance_to = seq
                # P3.E SLO: write -> retrievable-by-dense-lane lag.
                try:
                    from src.shared.metrics import ingestion_to_queryable_seconds
                    from src.shared.security import utc_now

                    if event_occurred_at is not None:
                        lag = (utc_now() - event_occurred_at).total_seconds()
                        if lag >= 0:
                            ingestion_to_queryable_seconds.observe(lag)
                except Exception:  # metrics never break the projection
                    pass
            except Exception as exc:
                # Likely transient — STOP advancing so this row is retried next
                # tick (at-least-once). Loud, never silent. A row that fails
                # deterministically will re-log each tick until the data is fixed
                # or the entity is deleted (then refresh_embedding no-ops).
                logger.error(
                    "embeddings_projection_row_failed",
                    seq=seq,
                    entity_type=et,
                    entity_id=eid,
                    error=str(exc),
                )
                failed += 1
                break

        await _set_cursor(session, "embeddings", advance_to)
        await session.commit()

    logger.info(
        "embeddings_projection_done", projected=projected, failed=failed, cursor=advance_to
    )
    return {"projected": projected, "failed": failed, "cursor": advance_to}
