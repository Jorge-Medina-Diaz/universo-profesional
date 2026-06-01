"""Arq task functions for long-running integration syncs.

Why move syncs here:
  * The HTTP request shouldn't block for 30-90s (Bright Data) or even 10-20s
    (GitHub) — the user sees the existing `SyncTaskTray` polling progress
    instead.
  * Workers run in their own process and can be cancelled at the OS level
    via `request_cancel()` (the soft-cancel flag we already persist).
  * One worker pool serves all users so we cap concurrency centrally.

Each task opens its own AsyncSession (via the same engine) and wires the
same use case classes the synchronous endpoints use. No business-logic
duplication.

Task contract: each function takes `(ctx, user_id: str, **kwargs)` and
returns the use-case result dict. Arq stores the result for `keep_result`
seconds; the frontend polls `/sync-runs` instead of waiting on the job.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from src.shared.worker_failures import handle_task_exception

logger = structlog.get_logger(__name__)


async def _new_session_scope(user_id: str):  # type: ignore[no-untyped-def]
    """Open a per-task session + apply RLS for the given user.

    Returns a context manager yielding the session. Caller is responsible
    for committing/rolling back through the use case's UoW.
    """
    from contextlib import asynccontextmanager

    from src.shared.db import get_session_factory, set_rls_user

    @asynccontextmanager
    async def _cm():
        factory = get_session_factory()
        async with factory() as session:
            await set_rls_user(session, UUID(user_id))
            yield session

    return _cm()


async def extract_knowledge_document(
    ctx: dict[str, Any], *, user_id: str, document_id: str
) -> dict[str, Any]:
    """Coherence pass over an ingested knowledge document (text → entities).

    Thin wrapper so the queue helper (which looks up tasks in this module)
    and the worker registry share one name; the real logic lives in the
    knowledge module.
    """
    from src.knowledge.application.extraction import run_extraction

    try:
        return await run_extraction(user_id=user_id, document_id=document_id)
    except Exception as exc:
        handle_task_exception(
            ctx,
            exc,
            task="extract_knowledge_document",
            user_id=user_id,
            document_id=document_id,
        )


async def run_github_sync_task(ctx: dict[str, Any], user_id: str) -> dict[str, Any]:
    """Run the GitHub sync in the background. Picked up by the Arq worker."""
    from src.integrations.application.github_sync import SyncGithub
    from src.integrations.infrastructure.repositories import (
        SqlExternalAccountRepository,
        SqlSyncRunsRepository,
    )
    from src.shared.uow import unit_of_work
    from src.universe.infrastructure.repositories import (
        SqlAlchemyExperienceRepository,
        SqlAlchemyInterestRepository,
        SqlAlchemyProjectRepository,
        SqlAlchemySkillRepository,
    )

    async with await _new_session_scope(user_id) as session:
        try:
            uc = SyncGithub(
                SqlExternalAccountRepository(session),
                SqlSyncRunsRepository(session),
                SqlAlchemyProjectRepository(session),
                SqlAlchemySkillRepository(session),
                SqlAlchemyInterestRepository(session),
                SqlAlchemyExperienceRepository(session),
            )
            async with unit_of_work(session) as uow:
                result = await uc.execute(user_id=user_id, uow=uow)
                await uow.commit()
            return result
        except Exception as exc:
            handle_task_exception(ctx, exc, task="run_github_sync_task", user_id=user_id)


async def run_linkedin_dma_sync_task(
    ctx: dict[str, Any], user_id: str
) -> dict[str, Any]:
    from src.integrations.application.linkedin_sync import SyncLinkedinDma
    from src.integrations.infrastructure.repositories import (
        SqlExternalAccountRepository,
        SqlImportSessionRepository,
        SqlSyncRunsRepository,
    )
    from src.shared.uow import unit_of_work

    async with await _new_session_scope(user_id) as session:
        try:
            uc = SyncLinkedinDma(
                SqlExternalAccountRepository(session),
                SqlImportSessionRepository(session),
                SqlSyncRunsRepository(session),
            )
            async with unit_of_work(session) as uow:
                result = await uc.execute(user_id=user_id, uow=uow)
                await uow.commit()
            return result
        except Exception as exc:
            handle_task_exception(
                ctx, exc, task="run_linkedin_dma_sync_task", user_id=user_id
            )


async def run_linkedin_brightdata_sync_task(
    ctx: dict[str, Any],
    user_id: str,
    linkedin_url: str | None = None,
    fresh: bool = False,
) -> dict[str, Any]:
    from src.integrations.application.linkedin_sync import SyncLinkedinBrightdata
    from src.integrations.infrastructure.repositories import (
        SqlExternalAccountRepository,
        SqlImportSessionRepository,
        SqlSyncRunsRepository,
    )
    from src.shared.uow import unit_of_work

    async with await _new_session_scope(user_id) as session:
        try:
            uc = SyncLinkedinBrightdata(
                SqlExternalAccountRepository(session),
                SqlImportSessionRepository(session),
                SqlSyncRunsRepository(session),
            )
            async with unit_of_work(session) as uow:
                result = await uc.execute(
                    user_id=user_id,
                    linkedin_url=linkedin_url,
                    fresh=fresh,
                    uow=uow,
                )
                await uow.commit()
            return result
        except Exception as exc:
            handle_task_exception(
                ctx, exc, task="run_linkedin_brightdata_sync_task", user_id=user_id
            )


async def resync_cron(ctx: dict[str, Any]) -> dict[str, Any]:
    """Weekly re-sync of stale GitHub connections (R10).

    Fans out one ``run_github_sync_task`` per connected GitHub account whose
    ``last_synced_at`` is null or older than 7 days — mirroring ``reminders_cron``.
    LinkedIn is intentionally EXCLUDED: a DMA re-sync only creates an uncommitted
    import_session (enriches nothing) and risks token/rate-limit failures; stale
    LinkedIn is surfaced instead by the IntegrationDriftProvider review card.
    GitHub re-sync writes entities directly through the coherence path, so it
    genuinely enriches. This only ENQUEUES; the sync task itself is fail-loud and
    soft-cancellable, so one connection's failure can't starve the batch.
    """
    from sqlalchemy import text

    from src.shared.db import with_user_session

    async with with_user_session(None) as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT DISTINCT user_id::text FROM external_accounts
                    WHERE provider = 'github'
                      AND (last_synced_at IS NULL
                           OR last_synced_at < now() - interval '7 days')
                    """
                )
            )
        ).all()
    user_ids = [r[0] for r in rows]
    if not user_ids:
        return {"connections": 0, "enqueued": 0, "mode": "noop"}

    redis = ctx.get("redis")
    if redis is None:
        # Degraded (no pool): run inline so dev/CLI still works. This DOES hit
        # the GitHub API — acceptable only because it's the Redis-down fallback.
        for uid in user_ids:
            try:
                await run_github_sync_task({}, uid)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("resync_inline_failed", user_id=uid, error=str(exc))
        return {"connections": len(user_ids), "mode": "inline"}

    enqueued = 0
    for uid in user_ids:
        try:
            await redis.enqueue_job("run_github_sync_task", user_id=uid)
            enqueued += 1
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("resync_enqueue_failed", user_id=uid, error=str(exc))
    logger.info("resync_cron_fanned_out", connections=len(user_ids), enqueued=enqueued)
    return {"connections": len(user_ids), "enqueued": enqueued, "mode": "arq"}
