"""Shared async Redis client.

Provides a singleton async Redis connection used by quota enforcement,
caching, and other backend features. The client is lazy-initialised on
first call and can be disposed cleanly during application shutdown.
"""
from __future__ import annotations

from redis.asyncio import Redis

from src.shared.config import get_settings

_redis_client: Redis | None = None


def get_redis() -> Redis:
    """Return the singleton async Redis client.

    The client is created on first call and reused thereafter.
    This is intentionally synchronous so consumers can obtain the
    client inside sync or async contexts without awaiting.
    """
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = Redis.from_url(
            settings.redis_url,
            decode_responses=False,
        )
    return _redis_client


async def dispose_redis() -> None:
    """Close the shared Redis connection and reset the singleton.

    Call this during application shutdown or between test runs.
    """
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
