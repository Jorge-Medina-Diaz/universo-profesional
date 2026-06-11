"""Shared utility functions and state for AG-UI endpoints."""
from __future__ import annotations

import asyncio
import base64
import re
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import Request
from jose import JWTError

from src.shared.errors import UnauthorizedError
from src.shared.security import decode_jwt

logger = structlog.get_logger(__name__)

# Hold references to fire-and-forget background tasks so they are not
# garbage-collected mid-flight (RUF006).
_background_tasks: set[asyncio.Task] = set()

# Per-user concurrent-stream cap. SSE chat streams are long-lived; without a
# cap a single user could open dozens in parallel and exhaust the DB pool.
# Redis-backed (cross-replica — required for multi-machine deploys); falls
# back to the in-memory counter if Redis is down so chat never hard-fails on
# a cache hiccup. The slot key carries a TTL so a crashed worker can't leak
# slots forever.
_MAX_CONCURRENT_STREAMS_PER_USER = 3
_STREAM_SLOT_TTL_SECONDS = 15 * 60  # > any sane run; expired slots self-heal
_active_streams: dict[str, int] = {}
_active_streams_lock = asyncio.Lock()


def _slot_key(user_id: str) -> str:
    return f"agui:streams:{user_id}"

_AGENT_DESCRIPTORS: dict[str, dict[str, Any]] = {
    "universe_coordinator": {
        "description": (
            "Coordinator team that decomposes user messages and delegates to "
            "entity + advisory + vertical specialists, then runs the coherence "
            "engine to keep the universe consistent over time."
        ),
        "capabilities": {
            "tools": True,
            "memory": True,
            "knowledge": True,
            "streaming": True,
        },
    },
}


async def _acquire_stream_slot(user_id: str) -> bool:
    try:
        from src.shared.redis import get_redis

        redis = get_redis()
        key = _slot_key(user_id)
        current = await redis.incr(key)
        # Refresh the TTL on every acquire — the key only needs to outlive
        # in-flight runs, not be a precise clock.
        await redis.expire(key, _STREAM_SLOT_TTL_SECONDS)
        if current > _MAX_CONCURRENT_STREAMS_PER_USER:
            await redis.decr(key)
            return False
        return True
    except Exception:
        logger.warning("stream_slot_redis_down_fallback_memory", user_id=user_id)
    async with _active_streams_lock:
        current = _active_streams.get(user_id, 0)
        if current >= _MAX_CONCURRENT_STREAMS_PER_USER:
            return False
        _active_streams[user_id] = current + 1
        return True


async def _release_stream_slot(user_id: str) -> None:
    try:
        from src.shared.redis import get_redis

        redis = get_redis()
        key = _slot_key(user_id)
        # DECR floor at 0 — a release after the TTL expired the key must not
        # leave a negative counter that would inflate the cap.
        current = await redis.decr(key)
        if current is not None and int(current) < 0:
            await redis.delete(key)
        return
    except Exception:
        logger.warning("stream_slot_redis_down_release_memory", user_id=user_id)
    async with _active_streams_lock:
        current = _active_streams.get(user_id, 0)
        if current <= 1:
            _active_streams.pop(user_id, None)
        else:
            _active_streams[user_id] = current - 1


def _runtime_info() -> dict[str, Any]:
    return {"version": "1", "mode": "sse", "agents": _AGENT_DESCRIPTORS}


def _ensure_known_agent(agent_id: str) -> None:
    if agent_id not in _AGENT_DESCRIPTORS:
        # Don't 404 — CopilotKit caches agent IDs and a transient 404 makes
        # the React layer give up. Map any unknown id to the coordinator.
        return
    return


def _extract_user_id_from_jwt(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    try:
        claims = decode_jwt(token, audience="cvs-saas-api")
    except JWTError as exc:
        raise UnauthorizedError(f"Invalid token: {exc}") from exc
    uid = claims.get("sub")
    if not uid:
        raise UnauthorizedError("Token missing sub")
    return str(uid)


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _decode_data_value(value: str) -> bytes:
    """Decode an InputContentDataSource value (raw base64 or data: URL)."""
    payload = value.split(",", 1)[1] if value.startswith("data:") else value
    return base64.b64decode(payload)


def _last_user_parts(messages: list[Any]) -> list[Any]:
    """Return the content parts of the latest user message, or [] if text/none."""
    for msg in reversed(messages):
        if getattr(msg, "role", None) != "user":
            continue
        content = getattr(msg, "content", None)
        return content if isinstance(content, list) else []
    return []


def _last_user_text(messages: list[Any]) -> str | None:
    """Return the plain-text content of the last user message."""
    for msg in reversed(messages):
        if getattr(msg, "role", None) == "user":
            content = getattr(msg, "content", None)
            if isinstance(content, str) and content.strip():
                return content.strip()
    return None


def _conversation_window(
    messages: list[Any], *, max_turns: int = 8, max_chars: int = 7000, focus_chars: int = 6000
) -> str | None:
    """Transcript of the recent conversation for the enrichment engine.

    A single user sentence ("el catálogo lo genera una IA") extracts poorly in
    isolation: cross-turn context is what lets the engine attach the AI catalog
    to the SAME ecommerce project mentioned three turns earlier and harvest the
    full corpus (stack, highlights, learnings). The last user message is marked
    as the FOCUS; agent turns are included as context only.

    Budgeting: the FOCO (the message being processed) gets the lion's share
    (`focus_chars`) — a long career dump is exactly what we want to harvest in
    full, so it must NOT be capped down to a context-line size. OLDER turns are
    capped small (they're only there for cross-turn linking), and whole leading
    turns are dropped to fit `max_chars`. The FOCO line is never head-sliced
    (that used to shear off the FOCO marker on long inputs). For genuinely huge
    pastes (a full multi-page CV) the import pipeline is the right path; chat
    enrichment handles a long paragraph/dump fully.
    """
    def _cap(s: str, n: int) -> str:
        s = s.strip()
        return s if len(s) <= n else s[:n] + " […]"

    # Index of the last user message = the FOCO (gets the generous budget).
    last_user_idx = -1
    for i, msg in enumerate(messages):
        if getattr(msg, "role", None) == "user" and isinstance(
            getattr(msg, "content", None), str
        ) and msg.content.strip():
            last_user_idx = i

    turns: list[str] = []
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        role = getattr(msg, "role", None)
        content = getattr(msg, "content", None)
        if not isinstance(content, str) or not content.strip():
            continue
        if role == "user":
            cap = focus_chars if i == last_user_idx else 800
            turns.append(f"Usuario: {_cap(content, cap)}")
        elif role == "assistant":
            turns.append(f"Agente: {_cap(content, 400)}")
        if len(turns) >= max_turns:
            break
    if not turns:
        return None
    turns.reverse()
    # mark the focus (last user line)
    for i in range(len(turns) - 1, -1, -1):
        if turns[i].startswith("Usuario: "):
            turns[i] = "Usuario (FOCO — extrae lo nuevo de aquí): " + turns[i][len("Usuario: "):]
            break
    # Assemble from the most-recent end backward, dropping WHOLE leading turns
    # until under max_chars — NEVER head-slice the joined string (that cut the
    # FOCO marker off the last user line on long inputs). The most-recent turn
    # is always kept even if it alone exceeds the budget.
    out: list[str] = []
    total = 0
    for line in reversed(turns):
        if out and total + len(line) + 1 > max_chars:
            break
        out.append(line)
        total += len(line) + 1
    out.reverse()
    return "\n".join(out)


def _ts_to_iso(ts: Any) -> str | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=UTC).isoformat()
    except Exception:
        return None
