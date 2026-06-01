"""Arq worker settings.

Tasks live in `*/infrastructure/tasks.py` modules; we import them here so
arq's startup discovers them.
"""
from __future__ import annotations

from typing import Any

from arq.connections import RedisSettings
from arq.cron import cron

from .config import get_settings


async def startup(ctx: dict[str, Any]) -> None:
    from .orm_loader import import_all_models
    from .logging import configure_logging

    configure_logging()
    # Wire observability for the worker process too (the API does this in its
    # lifespan). Sentry and OTel are isolated + guarded so one missing dep (e.g.
    # the OTLP exporter) never blocks boot OR skips the other — and failures are
    # loud, not a silent pass. init_sentry() is what makes worker_failures'
    # capture_exception reach Sentry, so it must not be coupled to OTel.
    import structlog as _structlog

    _obs_log = _structlog.get_logger(__name__)
    try:
        from .sentry_setup import init_sentry

        init_sentry()
    except Exception as exc:
        _obs_log.warning("worker_sentry_init_failed", error=str(exc))
    try:
        from .otel_setup import init_otel

        init_otel(service_name="cvs-saas-worker")
    except Exception as exc:
        _obs_log.warning("worker_otel_init_failed", error=str(exc))
    # Register EVERY ORM model so SQLAlchemy can resolve cross-table foreign
    # keys (e.g. skills.user_id → users.id) before any task flushes. Without
    # this, worker tasks that write entities (curator, syncs, knowledge
    # extraction) fail with "could not find table 'users'". The API does this
    # in its lifespan; the worker must do it too.
    import_all_models()
    ctx["settings"] = get_settings()


async def shutdown(ctx: dict[str, Any]) -> None:
    pass


def _build_redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings.from_dsn(settings.redis_url)


def _collect_functions() -> list[Any]:
    # Import lazily; tasks are wired here so the worker's task registry is complete.
    from src.agents.workflows.curator import curator_task
    from src.agents.workflows.session_digest import session_digest_task
    from src.documents.infrastructure.tasks import render_document
    from src.identity.infrastructure.tasks import (
        hard_delete_expired_accounts,
        send_email,
    )
    from src.integrations.infrastructure.tasks import (
        extract_knowledge_document,
        run_github_sync_task,
        run_linkedin_brightdata_sync_task,
        run_linkedin_dma_sync_task,
    )
    from src.mcp_server.infrastructure.tasks import (
        purge_expired_oauth_tokens,
    )
    from src.universe.infrastructure.reminder_tasks import process_reminders_task
    from src.universe.infrastructure.tasks import (
        compute_communities_task,
        enrich_universe_task,
        refresh_embedding,
    )

    return [
        refresh_embedding,
        enrich_universe_task,
        compute_communities_task,
        render_document,
        send_email,
        hard_delete_expired_accounts,
        curator_task,
        session_digest_task,
        run_github_sync_task,
        run_linkedin_dma_sync_task,
        run_linkedin_brightdata_sync_task,
        extract_knowledge_document,
        purge_expired_oauth_tokens,
        process_reminders_task,
    ]


def _collect_cron() -> list[Any]:
    from src.agents.workflows.curator import curator_cron
    from src.agents.workflows.session_digest import (
        session_digest_cron,
    )
    from src.mcp_server.infrastructure.tasks import (
        purge_expired_oauth_tokens,
    )
    from src.identity.infrastructure.lifecycle_tasks import lifecycle_cron
    from src.universe.infrastructure.reminder_tasks import reminders_cron

    return [
        # Daily curator sweep at 03:00 UTC.
        cron(curator_cron, hour={3}, minute={0}, run_at_startup=False),
        # Daily conversation-digest refresh at 03:30 UTC (compacts long
        # chats so the agent keeps a cheap long-term memory).
        cron(session_digest_cron, hour={3}, minute={30}, run_at_startup=False),
        # OAuth token purge at 04:00 UTC (after curator finishes).
        cron(
            purge_expired_oauth_tokens,
            hour={4},
            minute={0},
            run_at_startup=False,
        ),
        # Reminders scan + email digest at 07:00 UTC — a morning nudge,
        # after the overnight curator has tidied the universe.
        cron(reminders_cron, hour={7}, minute={0}, run_at_startup=False),
        # Day-1 lifecycle "finish setup" email at 08:00 UTC (re-engage
        # registered-but-never-activated users; once each, opt-out respected).
        cron(lifecycle_cron, hour={8}, minute={0}, run_at_startup=False),
    ]


class WorkerSettings:
    redis_settings = _build_redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    functions = _collect_functions()
    cron_jobs = _collect_cron()
    max_jobs = 10
    # Per-job wall-clock cap. The nightly curator now fans out into bounded
    # per-user jobs (see curator_cron), so no single job scans everyone.
    # 300s gives headroom for the heaviest task — the Bright Data LinkedIn
    # sync, whose HTTP client alone allows up to 180s.
    job_timeout = 300
    keep_result = 300
    # Write a Redis health key every 30s so the container healthcheck can probe
    # the job loop via arq.worker.check_health instead of a bare `pgrep`.
    health_check_interval = 30
    health_check_key = "arq:health-check"
