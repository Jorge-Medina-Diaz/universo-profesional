"""Arq tasks for the nudge engine (P3.A) — daily eligibility sweep.

Same fan-out shape as `reminder_tasks`: the cron enumerates active users and
enqueues one bounded job per user (inline fallback when no redis pool), so a
slow/failing user can't starve the rest. Expiry: pending nudges older than
14 days flip to `expired` so the surface never shows fossils.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select, text

from src.identity.infrastructure.orm import UserOrm
from src.shared.db import with_user_session
from src.shared.security import utc_now
from src.universe.application.nudges import sweep_user_nudges

logger = structlog.get_logger(__name__)


async def _activated_user_ids() -> list[str]:
    """Nudges only make sense for users who reached activation."""
    async with with_user_session(None) as session:
        rows = (
            await session.execute(
                select(UserOrm.id).where(
                    UserOrm.deleted_at.is_(None), UserOrm.activated_at.is_not(None)
                )
            )
        ).all()
    return [str(r[0]) for r in rows]


async def sweep_nudges_for_user(ctx: dict[str, Any], *, user_id: str) -> dict[str, Any]:
    uid = UUID(user_id)
    async with with_user_session(uid) as session:
        await session.execute(
            text(
                "UPDATE nudges SET status = 'expired' WHERE user_id = :uid "
                "AND status IN ('pending','surfaced') AND created_at < :cutoff"
            ),
            {"uid": user_id, "cutoff": utc_now() - timedelta(days=14)},
        )
        created = await sweep_user_nudges(session, uid)
        # Piggybacked hygiene: agno's memory manager stores near-identical
        # user memories on consecutive runs. Exact-duplicate rows are pure
        # noise that pollutes recall — keep the oldest of each.
        try:
            await session.execute(
                text(
                    "DELETE FROM ai.agno_memories a USING ai.agno_memories b "
                    "WHERE a.user_id = :uid AND b.user_id = :uid "
                    "AND a.memory->>'memory' = b.memory->>'memory' "
                    "AND a.memory_id > b.memory_id"
                ),
                {"uid": user_id},
            )
        except Exception as exc:  # hygiene must never break the sweep
            logger.warning("agno_memory_dedup_failed", user_id=user_id, error=str(exc))
    if created:
        logger.info("nudges_created", user_id=user_id, created=created)
    return {"created": created}


async def sweep_nudges_task(ctx: dict[str, Any], *, user_id: str) -> dict[str, Any]:
    """Arq task entry point — one user per job."""
    return await sweep_nudges_for_user(ctx, user_id=user_id)


async def nudge_sweep_cron(ctx: dict[str, Any]) -> dict[str, Any]:
    """Arq cron entry — daily, after the reminders cron."""
    user_ids = await _activated_user_ids()
    redis = ctx.get("redis")
    if redis is None:
        for uid in user_ids:
            try:
                await sweep_nudges_for_user(ctx, user_id=uid)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("nudge_sweep_user_failed", user_id=uid, error=str(exc))
        return {"users": len(user_ids), "mode": "inline"}

    enqueued = 0
    for uid in user_ids:
        try:
            await redis.enqueue_job("sweep_nudges_task", user_id=uid)
            enqueued += 1
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("nudge_enqueue_failed", user_id=uid, error=str(exc))
    logger.info("nudge_sweep_fanned_out", enqueued=enqueued)
    return {"users": len(user_ids), "enqueued": enqueued, "mode": "arq"}
