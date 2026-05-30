"""REST endpoint handlers (FastAPI route functions) for AG-UI."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy import text

from src.agents.interfaces.agui_core import (
    _ensure_known_agent,
    _extract_user_id_from_jwt,
    _runtime_info,
    _ts_to_iso,
)
from src.agents.interfaces.agui_streaming import _stream_chat
from src.identity.interfaces.api.deps import SessionDep
from src.shared.errors import UnauthorizedError
from src.shared.rate_limit import limiter

transport_router = APIRouter()

# Per-RUN rate limit. Applied ONLY to actual agent generations (run /
# run-multimodal), never to `connect` or `info`: CopilotKit keeps reopening
# the passive `connect` SSE channel (reconnects, StrictMode, navigation), so
# counting it against this budget produced a 429 storm in normal use. 60/min
# of real generations is far beyond any human cadence while still capping
# scripted cost bombs; the per-user concurrency cap below is the parallel
# guard. Keyed by JWT (rate_limit._key_func) → per-user, cross-replica (Redis).
_CHAT_RATE_LIMIT = "60/minute"
_REQUIRED_BODY = Body(...)

logger = structlog.get_logger(__name__)


@limiter.limit(_CHAT_RATE_LIMIT)
async def _limited_run(request: Request, run_body: dict[str, Any]) -> Any:
    """Run dispatch with the per-user run limiter applied. Used by the
    multiplexed POST /agui so CopilotKit's default transport (which funnels
    every run through that one endpoint) is rate-limited like the REST
    /agui/agent/{id}/run path — instead of bypassing the cap entirely."""
    return await _stream_chat(request=request, run_body=run_body, guard_concurrency=True)


@transport_router.get("/agui/info")
async def agui_info() -> dict[str, Any]:
    return _runtime_info()


@transport_router.get("/agui/status")
async def agui_status() -> dict[str, str]:
    return {"status": "available"}


@transport_router.get("/agui/threads")
async def agui_threads(
    request: Request,
    agentId: str | None = None,  # noqa: N803 — CopilotKit camelCases query params
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Single-chat model — return exactly one thread per user."""
    try:
        user_id = _extract_user_id_from_jwt(request)
    except UnauthorizedError:
        # Empty is the right UX for an anon/expired rehydration poll, but don't
        # mask it silently — log so an auth regression is observable.
        logger.warning("agui_threads_unauthorized")
        return {"threads": [], "joinCode": None, "nextCursor": None}

    now = datetime.now(UTC).isoformat()
    return {
        "threads": [
            {
                "id": f"main-{user_id}",
                "organizationId": "default",
                "agentId": agentId or "universe_coordinator",
                "createdById": str(user_id),
                "name": "Universo profesional",
                "archived": False,
                "createdAt": now,
                "updatedAt": now,
            }
        ],
        "joinCode": None,
        "nextCursor": None,
    }


@transport_router.get("/agui/threads/{thread_id}/messages")
async def agui_thread_messages(
    thread_id: str,
    request: Request,
    session: SessionDep,
    limit: int = Query(default=80, ge=1, le=400),
) -> dict[str, Any]:
    """List past messages for a thread so the chat UI can rehydrate on reload.

    Agno persists each turn as a `run` inside `ai.agno_sessions.runs` (JSONB
    array). We extract the user input + assistant output for each run and
    return them in chronological order. Tool calls and intermediate events
    are intentionally collapsed — the UI shows messages, not protocol noise.

    Auth: JWT required. We only let a user read THEIR own thread
    (`main-{user_id}`); any other thread_id 403s.
    """
    try:
        user_id = _extract_user_id_from_jwt(request)
    except UnauthorizedError:
        logger.warning("agui_thread_messages_unauthorized")
        return {"messages": [], "nextCursor": None}

    expected = f"main-{user_id}"
    if thread_id != expected:
        return JSONResponse(
            {"detail": "Forbidden"},
            status_code=403,
        )  # type: ignore[return-value]

    # Pull the agno session row. Agno writes to schema `ai`; that's the
    # default our `AsyncPostgresDb` configures in factory._build_db().
    row = (
        await session.execute(
            text(
                "SELECT runs FROM ai.agno_sessions "
                "WHERE session_id = :sid AND user_id = :uid"
            ),
            {"sid": expected, "uid": user_id},
        )
    ).first()
    if row is None or not row.runs:
        return {"messages": [], "nextCursor": None}

    runs: list[dict[str, Any]] = row.runs or []
    messages: list[dict[str, Any]] = []
    for run in runs:
        rid = str(run.get("run_id") or "")
        created = run.get("created_at")
        user_content = (run.get("input") or {}).get("input_content")
        if isinstance(user_content, str) and user_content.strip():
            messages.append(
                {
                    "id": f"{rid}-u",
                    "role": "user",
                    "content": user_content,
                    "createdAt": _ts_to_iso(created),
                }
            )
        assistant_content = run.get("content")
        if isinstance(assistant_content, str) and assistant_content.strip():
            messages.append(
                {
                    "id": f"{rid}-a",
                    "role": "assistant",
                    "content": assistant_content,
                    "createdAt": _ts_to_iso(created),
                }
            )

    # Most recent N — chat UIs render bottom-up.
    if len(messages) > limit:
        messages = messages[-limit:]
    return {"messages": messages, "nextCursor": None}


@transport_router.post("/agui")
async def agui_single_endpoint(
    request: Request,
    body: dict[str, Any] = _REQUIRED_BODY,
) -> Any:
    # NOTE: no blanket @limiter here — this envelope multiplexes info/connect/
    # run, and only runs should be rate-limited. The run limit is enforced
    # per-method below; connect/info pass through freely.
    method = body.get("method") if isinstance(body, dict) else None

    if method == "info":
        return JSONResponse(_runtime_info())

    if method == "agent/stop":
        return Response(status_code=204)

    if method in ("agent/connect", "agent/run"):
        inner = body.get("body") or {}
        if method == "agent/run":
            # Apply the per-user run limiter (the REST /run path has it; this
            # multiplexed envelope previously bypassed it entirely).
            return await _limited_run(request, inner)
        # `connect` is a long-lived passive SSE channel CopilotKit keeps open —
        # NOT rate-limited and doesn't consume a concurrency slot.
        return await _stream_chat(
            request=request, run_body=inner, guard_concurrency=False
        )

    # No envelope → treat as a raw RunAgentInput for backwards compat (a run).
    if method is None and isinstance(body, dict):
        return await _limited_run(request, body)

    return JSONResponse(
        {"detail": f"Unknown method {method!r}"}, status_code=400
    )


@transport_router.post("/agui/agent/{agent_id}/connect")
async def agui_agent_connect(
    agent_id: str, request: Request, body: dict[str, Any] = _REQUIRED_BODY
) -> StreamingResponse:
    _ensure_known_agent(agent_id)
    # connect = passive SSE channel CopilotKit reopens on every reconnect /
    # remount → deliberately NOT rate-limited (counting it 429-stormed real
    # users) and doesn't consume a concurrency slot.
    return await _stream_chat(request=request, run_body=body)


@transport_router.post("/agui/agent/{agent_id}/run")
@limiter.limit(_CHAT_RATE_LIMIT)
async def agui_agent_run(
    agent_id: str, request: Request, body: dict[str, Any] = _REQUIRED_BODY
) -> StreamingResponse:
    _ensure_known_agent(agent_id)
    return await _stream_chat(
        request=request, run_body=body, guard_concurrency=True
    )
