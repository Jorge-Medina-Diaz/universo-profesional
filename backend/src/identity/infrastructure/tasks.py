"""Arq tasks for the Identity context."""
from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import delete
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.identity.infrastructure.orm import UserOrm
from src.shared.db import get_session_factory
from src.shared.security import utc_now

logger = structlog.get_logger(__name__)


async def send_email(
    ctx: dict[str, Any],
    *,
    to: str,
    subject: str,
    body: str,
    html: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Background email send — used to decouple SMTP/HTTP from request path.

    Provider is selected from settings (mock vs brevo vs postmark). On
    transient failures we retry up to 3 times with exponential backoff so
    the worker recovers from short SMTP/API outages without losing the
    message.
    """
    from src.identity.application.ports import EmailSendError
    from src.identity.infrastructure.email_sender import get_email_sender

    sender = get_email_sender()

    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((EmailSendError, ConnectionError, TimeoutError)),
        reraise=True,
    ):
        with attempt:
            await sender.send(
                to=to,
                subject=subject,
                body_text=body,
                body_html=html,
                tags=tags or [],
            )
    return {"ok": True, "to": to, "subject": subject}


async def enqueue_transactional_email(
    *,
    user_id: UUID,
    template: str,
    context: dict[str, Any] | None = None,
) -> None:
    """Render a transactional template + enqueue the send.

    Resolves the user's email + locale, renders the template, and pushes a
    `send_email` job onto the Arq queue. Falls back to inline execution if
    Redis is unreachable (same pattern as integrations.queue).
    """
    from src.identity.infrastructure.email_templates import render_template
    from src.identity.infrastructure.repositories import SqlAlchemyUserRepository

    factory = get_session_factory()
    async with factory() as session:
        repo = SqlAlchemyUserRepository(session)
        user = await repo.get_by_id(user_id)
        if user is None:
            logger.warning("transactional_email_no_user", user_id=str(user_id))
            return

    rendered = render_template(
        template,
        locale=(user.locale or "es-ES").split("-")[0],
        context={"display_name": user.display_name or user.email, **(context or {})},
    )

    # Try to enqueue on Arq; fall back to inline send.
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        from src.shared.config import get_settings

        pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
        try:
            await pool.enqueue_job(
                "send_email",
                to=str(user.email),
                subject=rendered["subject"],
                body=rendered["text"],
                html=rendered.get("html"),
                tags=[template],
            )
        finally:
            await pool.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("email_enqueue_fallback_inline", error=str(exc))
        await send_email(
            {},
            to=str(user.email),
            subject=rendered["subject"],
            body=rendered["text"],
            html=rendered.get("html"),
            tags=[template],
        )


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
