"""Token-quota enforcement backed by Redis.

Daily token budgets per plan:
  Free  -> 10_000
  Premium -> 100_000
  Pro   -> unlimited (None)
"""
from __future__ import annotations

from uuid import UUID

from src.shared.redis import get_redis

_DAILY_BUDGET: dict[str, int | None] = {
    "free": 10_000,
    "premium": 100_000,
    "pro": None,
}

_REDIS_KEY_PREFIX = "token_quota"


def _key(user_id: UUID) -> str:
    return f"{_REDIS_KEY_PREFIX}:{user_id}"


async def check_token_quota(*, user_id: UUID, plan: str, requested_tokens: int = 0) -> bool:
    """Return True if the user is within their daily token budget.

    If `requested_tokens` is provided, the check reserves that amount
    atomically so concurrent requests don't overshoot.
    """
    budget = _DAILY_BUDGET.get(plan.lower())
    if budget is None:
        return True  # unlimited

    redis = get_redis()
    key = _key(user_id)

    # Use Redis INCRBY with TTL (sliding 24h window)
    pipe = redis.pipeline()
    pipe.incrby(key, requested_tokens or 0)
    pipe.ttl(key)
    current, ttl = await pipe.execute()

    if ttl == -1:
        # Key existed without TTL (shouldn't happen), set 24h
        await redis.expire(key, 86_400)

    return current <= budget


async def get_tokens_used_today(user_id: UUID) -> int:
    """Return tokens consumed today for a user."""
    redis = get_redis()
    val = await redis.get(_key(user_id))
    return int(val or 0)


async def increment_token_usage(user_id: UUID, tokens: int) -> None:
    """Record token consumption (used when the exact cost is known post-call)."""
    redis = get_redis()
    key = _key(user_id)
    pipe = redis.pipeline()
    pipe.incrby(key, tokens)
    pipe.expire(key, 86_400)
    await pipe.execute()
