"""Lifecycle email tasks (R19): re-engage users who registered but never activated.

Builds on the server-side onboarding/activation state (R3): a daily cron emails
a one-time "finish your setup" nudge to users who created an account but never
reached activation or completed onboarding. Reuses the transactional-email
infra; respects the per-user notify opt-out; sends at most once.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text

from src.shared.db import with_user_session

logger = structlog.get_logger(__name__)


async def lifecycle_cron(ctx: dict[str, Any]) -> dict[str, Any]:
    """Day-1 "finish setup" email.

    Eligible = registered 1–14 days ago, never activated, never completed
    onboarding, opted in, and not yet emailed. We mark day1_email_sent_at BEFORE
    sending (at-most-once: a dropped email beats re-sending nightly — the same
    ordering the reminders dispatch uses). The 14-day floor avoids spamming
    long-dormant accounts on first deploy.
    """
    from src.identity.infrastructure.tasks import enqueue_transactional_email

    async with with_user_session(None) as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT id::text FROM users
                    WHERE deleted_at IS NULL
                      AND activated_at IS NULL
                      AND onboarding_completed_at IS NULL
                      AND day1_email_sent_at IS NULL
                      AND notify_email_reminders = true
                      AND created_at <= now() - interval '1 day'
                      AND created_at >= now() - interval '14 days'
                    """
                )
            )
        ).all()
        user_ids = [r[0] for r in rows]
        if not user_ids:
            return {"sent": 0}
        await session.execute(
            text(
                "UPDATE users SET day1_email_sent_at = now() WHERE id::text = ANY(:ids)"
            ),
            {"ids": user_ids},
        )
        await session.commit()

    sent = 0
    for uid in user_ids:
        try:
            await enqueue_transactional_email(user_id=UUID(uid), template="finish_setup")
            sent += 1
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("lifecycle_email_failed", user_id=uid, error=str(exc))
    logger.info("lifecycle_day1_sent", count=sent)
    return {"sent": sent}
