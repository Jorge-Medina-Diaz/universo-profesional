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
    from .db import import_all_models
    from .logging import configure_logging

    configure_logging()
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
    from src.agents.workflows.curator import curator_task  # noqa: WPS433
    from src.agents.workflows.session_digest import session_digest_task  # noqa: WPS433
    from src.documents.infrastructure.tasks import render_document  # noqa: WPS433
    from src.identity.infrastructure.tasks import (  # noqa: WPS433
        hard_delete_expired_accounts,
        send_email,
    )
    from src.integrations.infrastructure.tasks import (  # noqa: WPS433
        extract_knowledge_document,
        run_github_sync_task,
        run_linkedin_brightdata_sync_task,
        run_linkedin_dma_sync_task,
    )
    from src.mcp_server.infrastructure.tasks import (  # noqa: WPS433
        purge_expired_oauth_tokens,
    )
    from src.universe.infrastructure.tasks import (  # noqa: WPS433
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
    ]


def _collect_cron() -> list[Any]:
    from src.agents.workflows.curator import curator_cron  # noqa: WPS433
    from src.agents.workflows.session_digest import (  # noqa: WPS433
        session_digest_cron,
    )
    from src.mcp_server.infrastructure.tasks import (  # noqa: WPS433
        purge_expired_oauth_tokens,
    )

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
