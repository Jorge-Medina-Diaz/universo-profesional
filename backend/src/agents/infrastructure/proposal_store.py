"""In-memory proposal cache with TTL.

For MVP we use a simple dict keyed by ``proposal:{user_id}:{proposal_id}``.
In production this should be backed by Redis so proposals survive process
restarts and work across replicas.
"""
from __future__ import annotations

import time
from typing import Any

_PROPOSAL_TTL_SECONDS = 300  # 5 minutes
_store: dict[str, dict[str, Any]] = {}


def _key(user_id: str, proposal_id: str) -> str:
    return f"proposal:{user_id}:{proposal_id}"


def set_proposal(
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
    """Store a pending proposal."""
    _store[_key(user_id, proposal_id)] = {
        "entity_type": entity_type,
        "entity_data": entity_data,
        "action": action,
        "confidence": confidence,
        "reason": reason,
        "thread_id": thread_id,
        "created_at": time.time(),
    }


def get_proposal(user_id: str, proposal_id: str) -> dict[str, Any] | None:
    """Retrieve a proposal if it exists and hasn't expired."""
    key = _key(user_id, proposal_id)
    item = _store.get(key)
    if item is None:
        return None
    if time.time() - item["created_at"] > _PROPOSAL_TTL_SECONDS:
        _store.pop(key, None)
        return None
    return item


def delete_proposal(user_id: str, proposal_id: str) -> None:
    _store.pop(_key(user_id, proposal_id), None)


def cleanup_expired() -> int:
    """Remove expired entries. Returns number removed."""
    now = time.time()
    expired = [
        k for k, v in _store.items() if now - v["created_at"] > _PROPOSAL_TTL_SECONDS
    ]
    for k in expired:
        _store.pop(k, None)
    return len(expired)
