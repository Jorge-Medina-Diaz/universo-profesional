"""Arq tasks for the Identity context."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

import structlog
from sqlalchemy import delete

from src.identity.infrastructure.orm import UserOrm
from src.shared.db import get_session_factory
from src.shared.security import utc_now

logger = structlog.get_logger(__name__)


async def send_email(ctx: dict[str, Any], *, to: str, subject: str, body: str) -> None:
    """Background email send — used to decouple SMTP from HTTP requests."""
    from src.identity.infrastructure.email_sender import MockEmailSender

    sender = MockEmailSender()
    await sender._send(to=to, subject=subject, body=body)  # noqa: SLF001


async def hard_delete_expired_accounts(ctx: dict[str, Any]) -> int:
    """Scheduled task: hard-delete users whose `deleted_at` > 30 days ago.

    Run nightly (cron via arq's `cron` jobs in a future iteration; for MVP
    we expose this as a callable that the worker can run manually).
    """
    cutoff = utc_now() - timedelta(days=30)
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            delete(UserOrm)
            .where(UserOrm.deleted_at.is_not(None))
            .where(UserOrm.deleted_at < cutoff)
            .returning(UserOrm.id)
        )
        result = await session.execute(stmt)
        ids = [str(r[0]) for r in result.fetchall()]
        await session.commit()
    logger.info("hard_deleted_accounts", count=len(ids), ids=ids)
    return len(ids)
