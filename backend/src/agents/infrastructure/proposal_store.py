"""Redis-backed proposal cache with TTL.

HITL proposals must survive process restarts and be shared across workers /
replicas: the process that *stores* a proposal during the agent run is rarely
the one that *resolves* the user's confirm/reject click. A module-level dict
silently lost proposals under any multi-worker deployment, so the confirm card
404'd. We back the store with the shared async Redis client (also used by arq),
keyed by ``proposal:{user_id}:{proposal_id}`` with a native key TTL.
"""
from __future__ import annotations

import json
import time
from typing import Any

from src.shared.redis import get_redis

# P2: 24h — a card left open while the user thinks it over must not 404
# on confirm (the old 5-minute TTL did exactly that). Resolution deletes
# the key, so the window only bounds ABANDONED proposals.
_PROPOSAL_TTL_SECONDS = 24 * 3600


def _key(user_id: str, proposal_id: str) -> str:
    return f"proposal:{user_id}:{proposal_id}"


async def set_proposal(
    user_id: str,
    proposal_id: str,
    *,
    entity_type: str,
    entity_data: dict[str, Any],
    action: str = "create",
    confidence: float = 0.85,
    reason: str = "Propuesta generada por el agente",
    thread_id: str | None = None,
) -> None:
    """Store a pending proposal with a native Redis TTL."""
    payload = {
        "entity_type": entity_type,
        "entity_data": entity_data,
        "action": action,
        "confidence": confidence,
        "reason": reason,
        "thread_id": thread_id,
        "created_at": time.time(),
    }
    await get_redis().set(
        _key(user_id, proposal_id),
        json.dumps(payload, default=str),
        ex=_PROPOSAL_TTL_SECONDS,
    )


async def get_proposal(user_id: str, proposal_id: str) -> dict[str, Any] | None:
    """Retrieve a proposal if it exists and hasn't expired (Redis handles TTL)."""
    raw = await get_redis().get(_key(user_id, proposal_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


async def delete_proposal(user_id: str, proposal_id: str) -> None:
    await get_redis().delete(_key(user_id, proposal_id))
