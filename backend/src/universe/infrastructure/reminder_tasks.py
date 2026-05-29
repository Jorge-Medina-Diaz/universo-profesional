"""Arq tasks for the reminders engine: nightly scan + email dispatch.

The reminders model, scan logic and REST surface already existed; what was
missing was anything that actually *notifies* the user. These tasks close that
loop:

  • `reminders_cron` fans the work out into one bounded job per active user
    (same pattern as the curator), so a slow/failing user can't starve the rest.
  • `process_reminders_for_user` scans the user's universe for new reminders,
    then emails a single digest of the reminders that are due and not yet
    dispatched — respecting the per-user `notify_email_reminders` opt-out — and
    marks them dispatched so they're never emailed twice.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select, update

from src.identity.infrastructure.orm import UserOrm
from src.shared.db import with_user_session
from src.shared.security import utc_now
from src.universe.application.ports.orm import ReminderOrm

logger = structlog.get_logger(__name__)


async def _all_active_user_ids() -> list[str]:
    """Every non-deleted user. Reminders matter even for users who haven't
    touched their universe recently (e.g. a certification quietly expiring)."""
    async with with_user_session(None) as session:
        rows = (
            await session.execute(
                select(UserOrm.id).where(UserOrm.deleted_at.is_(None))
            )
        ).all()
    return [str(r[0]) for r in rows]


async def process_reminders_for_user(ctx: dict[str, Any], *, user_id: str) -> dict[str, Any]:
    """Scan + dispatch reminders for a single user.

    Returns a small summary dict for observability. Never raises for an
    individual user's data problem — logs and returns instead, so the cron
    batch keeps going.
    """
    from src.universe.application.reminders import ScanReminders

    uid = UUID(user_id)
    created = 0
    dispatched = 0
    async with with_user_session(uid) as session:
        # 1. Generate any new reminders from current universe state.
        try:
            created = await ScanReminders(session).execute(user_id=uid)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("reminder_scan_failed", user_id=user_id, error=str(exc))

        # 2. Find reminders that are due and not yet dispatched/dismissed.
        now = utc_now()
        due_rows = (
            await session.execute(
                select(ReminderOrm)
                .where(ReminderOrm.user_id == uid)
                .where(ReminderOrm.dismissed_at.is_(None))
                .where(ReminderOrm.dispatched_at.is_(None))
                .where(ReminderOrm.due_at <= now)
                .order_by(ReminderOrm.due_at)
            )
        ).scalars().all()

        if not due_rows:
            await session.commit()
            return {"created": created, "dispatched": 0}

        # 3. Respect the per-user opt-out. We still mark them dispatched so an
        #    opted-out user isn't re-considered every night, and they remain
        #    visible in-app until dismissed.
        opted_in = await session.scalar(
            select(UserOrm.notify_email_reminders).where(UserOrm.id == uid)
        )

        if opted_in:
            await _send_digest(uid, due_rows)
            dispatched = len(due_rows)

        await session.execute(
            update(ReminderOrm)
            .where(ReminderOrm.id.in_([r.id for r in due_rows]))
            .values(dispatched_at=now)
        )
        await session.commit()

    logger.info(
        "reminders_processed", user_id=user_id, created=created, dispatched=dispatched
    )
    return {"created": created, "dispatched": dispatched}


async def _send_digest(user_id: UUID, reminders: list[ReminderOrm]) -> None:
    from src.identity.infrastructure.tasks import enqueue_transactional_email

    await enqueue_transactional_email(
        user_id=user_id,
        template="reminders_digest",
        context={
            "reminders": [{"title": r.title, "body": r.body} for r in reminders],
            "count": len(reminders),
        },
    )


async def process_reminders_task(ctx: dict[str, Any], *, user_id: str) -> dict[str, Any]:
    """Arq task entry point — called by the daily cron with a single user id."""
    return await process_reminders_for_user(ctx, user_id=user_id)


async def reminders_cron(ctx: dict[str, Any]) -> dict[str, Any]:
    """Arq cron entry — fans the daily scan+dispatch out into per-user jobs.

    Falls back to an inline sweep if the redis pool isn't on the context
    (e.g. a manual invocation in a test/CLI)."""
    user_ids = await _all_active_user_ids()
    redis = ctx.get("redis")
    if redis is None:
        for uid in user_ids:
            try:
                await process_reminders_for_user(ctx, user_id=uid)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("reminders_user_failed", user_id=uid, error=str(exc))
        return {"users": len(user_ids), "mode": "inline"}

    enqueued = 0
    for uid in user_ids:
        try:
            await redis.enqueue_job("process_reminders_task", user_id=uid)
            enqueued += 1
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("reminders_enqueue_failed", user_id=uid, error=str(exc))
    logger.info("reminders_cron_fanned_out", enqueued=enqueued)
    return {"users": len(user_ids), "enqueued": enqueued, "mode": "arq"}
