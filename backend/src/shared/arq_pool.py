"""Process-wide arq pool (PENDING fix: Redis.close RuntimeWarning).

Previously every `ArqEmbeddingScheduler()` (one per upsert/note call site)
and `integrations.queue` opened its OWN arq pool and never closed it — a
connection leak plus `RuntimeWarning: coroutine 'Redis.close' was never
awaited` when those clients were garbage-collected. One cached pool per
process, disposed from the app lifespan.
"""
from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_pool: Any | None = None
_failed: bool = False


async def get_arq_pool() -> Any | None:
    """Cached arq pool; None when Redis is unreachable (callers fall back
    inline). A failed connect is retried on the next call."""
    global _pool, _failed
    if _pool is not None:
        return _pool
    from arq import create_pool
    from arq.connections import RedisSettings

    from src.shared.config import get_settings

    try:
        _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
        _failed = False
    except Exception as exc:
        if not _failed:  # log once per outage, not per call
            logger.warning("arq_pool_unavailable", error=str(exc))
        _failed = True
        _pool = None
    return _pool


async def dispose_arq_pool() -> None:
    global _pool
    if _pool is not None:
        try:
            await _pool.aclose()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("arq_pool_dispose_failed", error=str(exc))
        _pool = None
