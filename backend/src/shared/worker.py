"""Arq worker settings.

Tasks live in `*/infrastructure/tasks.py` modules; we import them here so
arq's startup discovers them.
"""
from __future__ import annotations

from typing import Any

from arq.connections import RedisSettings

from .config import get_settings


async def startup(ctx: dict[str, Any]) -> None:
    from .logging import configure_logging

    configure_logging()
    ctx["settings"] = get_settings()


async def shutdown(ctx: dict[str, Any]) -> None:
    pass


def _build_redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings.from_dsn(settings.redis_url)


def _collect_functions() -> list[Any]:
    # Import lazily; tasks are wired here so the worker's task registry is complete.
    from src.universe.infrastructure.tasks import (  # noqa: WPS433
        refresh_embedding,
    )
    from src.documents.infrastructure.tasks import render_document  # noqa: WPS433
    from src.identity.infrastructure.tasks import (  # noqa: WPS433
        hard_delete_expired_accounts,
        send_email,
    )

    return [
        refresh_embedding,
        render_document,
        send_email,
        hard_delete_expired_accounts,
    ]


class WorkerSettings:
    redis_settings = _build_redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    functions = _collect_functions()
    max_jobs = 10
    job_timeout = 120
    keep_result = 300
