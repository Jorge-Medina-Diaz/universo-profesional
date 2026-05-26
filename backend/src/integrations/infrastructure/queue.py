"""Lazy Arq pool + helper to enqueue integration sync tasks.

Why not inject the pool everywhere: the endpoints that fire syncs are HTTP
handlers with their own request session; passing a pool through FastAPI
deps would add boilerplate for little gain. This module owns a singleton
pool + a helper that the routers can call directly.

Fallback: when Redis is unreachable (tests, dev offline), we degrade to
running the task in-process. The run still hits the DB and updates the
sync_runs row, so the SyncTaskTray UI still works — it just blocks the
request for the duration.
"""
from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


_pool: Any | None = None


async def _get_pool() -> Any | None:
    """Return a cached Arq pool, or None if Redis is down."""
    global _pool
    if _pool is not None:
        return _pool
    from arq import create_pool
    from arq.connections import RedisSettings

    from src.shared.config import get_settings

    settings = get_settings()
    try:
        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    except Exception as exc:
        logger.warning("arq_pool_unavailable", error=str(exc))
        _pool = None
    return _pool


async def enqueue_integration_task(name: str, **kwargs: Any) -> dict[str, Any]:
    """Enqueue a task by name on the integrations worker.

    Returns `{queued: bool, job_id: str|None, mode: "arq"|"inline"}`. When
    Redis is unavailable we fall back to running the task inline so the
    endpoint still does the right thing — at the cost of blocking the
    request. The frontend can poll `/sync-runs` either way.
    """
    pool = await _get_pool()
    if pool is None:
        # Inline fallback. Import the task module here to avoid pulling Arq
        # state into the request hot-path when the pool is available.
        from src.integrations.infrastructure import tasks as _tasks

        fn = getattr(_tasks, name, None)
        if fn is None:
            return {"queued": False, "job_id": None, "mode": "inline", "error": "unknown_task"}
        result = await fn({}, **kwargs)
        return {"queued": True, "job_id": None, "mode": "inline", "result": result}

    job = await pool.enqueue_job(name, **kwargs)
    return {
        "queued": job is not None,
        "job_id": getattr(job, "job_id", None) if job else None,
        "mode": "arq",
    }
