"""AG-UI endpoints — runtime discovery + chat streams.

CopilotKit's React core auto-detects two transports:

  REST mode
    GET  /agui/info                      → runtime catalogue
    GET  /agui/threads?agentId=…         → thread list (we return 1 per user)
    POST /agui/agent/{agentId}/connect   → SSE stream
    POST /agui/agent/{agentId}/run       → SSE stream

  Single-endpoint mode
    POST /agui                           → body envelope discriminated by `method`:
                                           {"method": "info"}                          → JSON info
                                           {"method": "agent/connect", body: RunInput} → SSE
                                           {"method": "agent/run",     body: RunInput} → SSE
                                           {"method": "agent/stop"}                    → 204

We expose both so any CopilotKit version works. Discovery and status are
public; chat streams require a valid JWT (we override `forwarded_props.user_id`
and pin `thread_id = main-<user_id>` ourselves).
"""
from __future__ import annotations

import asyncio
import re
from typing import Any

import structlog
from ag_ui.core import EventType, RunAgentInput, RunErrorEvent
from ag_ui.encoder import EventEncoder
from agno.os.interfaces.agui.router import run_team
from fastapi import APIRouter, Body, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse
from jose import JWTError
from sqlalchemy import text

from src.identity.interfaces.api.deps import SessionDep
from src.shared.errors import UnauthorizedError
from src.shared.rate_limit import limiter
from src.shared.security import decode_jwt

logger = structlog.get_logger(__name__)

router = APIRouter()

# Per-RUN rate limit. Applied ONLY to actual agent generations (run /
# run-multimodal), never to `connect` or `info`: CopilotKit keeps reopening
# the passive `connect` SSE channel (reconnects, StrictMode, navigation), so
# counting it against this budget produced a 429 storm in normal use. 60/min
# of real generations is far beyond any human cadence while still capping
# scripted cost bombs; the per-user concurrency cap below is the parallel
# guard. Keyed by JWT (rate_limit._key_func) → per-user, cross-replica (Redis).
_CHAT_RATE_LIMIT = "60/minute"

# Per-user concurrent-stream cap. SSE chat streams are long-lived; without a
# cap a single user could open dozens in parallel and exhaust the DB pool.
# This guard is per-process (in-memory) — a pragmatic safety net; the Redis
# rate limit above is the cross-replica control.
_MAX_CONCURRENT_STREAMS_PER_USER = 3
_active_streams: dict[str, int] = {}
_active_streams_lock = asyncio.Lock()


async def _acquire_stream_slot(user_id: str) -> bool:
    async with _active_streams_lock:
        current = _active_streams.get(user_id, 0)
        if current >= _MAX_CONCURRENT_STREAMS_PER_USER:
            return False
        _active_streams[user_id] = current + 1
        return True


async def _release_stream_slot(user_id: str) -> None:
    async with _active_streams_lock:
        current = _active_streams.get(user_id, 0)
        if current <= 1:
            _active_streams.pop(user_id, None)
        else:
            _active_streams[user_id] = current - 1


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

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


def _runtime_info() -> dict[str, Any]:
    return {"version": "1", "mode": "sse", "agents": _AGENT_DESCRIPTORS}


@router.get("/agui/info")
async def agui_info() -> dict[str, Any]:
    return _runtime_info()


@router.get("/agui/status")
async def agui_status() -> dict[str, str]:
    return {"status": "available"}


@router.get("/agui/threads")
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
        return {"threads": [], "joinCode": None, "nextCursor": None}

    now = "2026-05-19T00:00:00Z"
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


# ---------------------------------------------------------------------------
# Scroll-back — re-hydrate previous turns from agno_sessions.runs JSONB.
# ---------------------------------------------------------------------------


@router.get("/agui/threads/{thread_id}/messages")
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


def _ts_to_iso(ts: Any) -> str | None:
    if ts is None:
        return None
    try:
        from datetime import datetime, timezone

        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Single-endpoint transport (envelope discriminated by `method`)
# ---------------------------------------------------------------------------


@router.post("/agui")
async def agui_single_endpoint(
    request: Request,
    body: dict[str, Any] = Body(...),
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
        is_run = method == "agent/run"
        # Only bound actual RUNs; `connect` is a long-lived passive SSE
        # channel CopilotKit keeps open and must not consume a slot or quota.
        # Run cost is capped per-user by the concurrency guard below (and, on
        # the active REST transport, by the @limiter on /run).
        return await _stream_chat(
            request=request,
            run_body=inner,
            guard_concurrency=is_run,
        )

    # No envelope → treat as a raw RunAgentInput for backwards compat.
    if method is None and isinstance(body, dict):
        return await _stream_chat(
            request=request, run_body=body, guard_concurrency=True
        )

    return JSONResponse(
        {"detail": f"Unknown method {method!r}"}, status_code=400
    )


# ---------------------------------------------------------------------------
# REST transport (CopilotKit's preferred path when /info is reachable)
# ---------------------------------------------------------------------------


@router.post("/agui/agent/{agent_id}/connect")
async def agui_agent_connect(
    agent_id: str, request: Request, body: dict[str, Any] = Body(...)
) -> StreamingResponse:
    _ensure_known_agent(agent_id)
    # connect = passive SSE channel CopilotKit reopens on every reconnect /
    # remount → deliberately NOT rate-limited (counting it 429-stormed real
    # users) and doesn't consume a concurrency slot.
    return await _stream_chat(request=request, run_body=body)


@router.post("/agui/agent/{agent_id}/run")
@limiter.limit(_CHAT_RATE_LIMIT)
async def agui_agent_run(
    agent_id: str, request: Request, body: dict[str, Any] = Body(...)
) -> StreamingResponse:
    _ensure_known_agent(agent_id)
    return await _stream_chat(
        request=request, run_body=body, guard_concurrency=True
    )


# ---------------------------------------------------------------------------
# Multi-modal endpoint — bypass AG-UI to send images to the LLM directly.
#
# `ag_ui.core.UserMessage.content` is `str` only, so the AG-UI transport
# can't carry images. We expose a parallel multipart endpoint that takes
# (text, images[]) and calls `team.arun(input=text, images=[Image(...)])`
# directly. The response is non-streaming (return the assistant text).
#
# The frontend uses this when the user drops an image into the chat: it
# POSTs text + the image, gets back the assistant reply, and injects it
# into the chat as a regular assistant message.
# ---------------------------------------------------------------------------


_ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_IMAGE_BYTES = 8 * 1024 * 1024
_MAX_IMAGES_PER_CALL = 3
_MAX_USER_TEXT_CHARS = 10_000  # cap on a single multimodal/chat input


@router.post("/agui/agent/{agent_id}/run-multimodal")
@limiter.limit(_CHAT_RATE_LIMIT)
async def agui_run_multimodal(
    agent_id: str,
    request: Request,
    text: str = Form(...),
    images: list[UploadFile] = File(default=[]),
    stream: bool = Form(default=True),
):
    """Send a single turn (text + optional images) to the team.

    Default behaviour is to stream the assistant reply as Server-Sent Events
    (`data: {"type": "chunk", "content": "..."}\\n\\n` per delta + a final
    `data: {"type": "done", "run_id": "…"}\\n\\n`). Pass `stream=false`
    in the form data to get a single JSON response instead — useful for
    quick scripts and tests.

    Design decision (Sprint J): we DELIBERATELY do NOT relay
    `external_execution=True` tool calls in this stream. The frontend wires
    HITL cards (`propose_*`) through the CopilotKit AG-UI pipeline; that
    machinery is not active here. The contract is therefore:

      1. Multimodal turn → assistant responds in plain text (classifying,
         extracting, suggesting next actions) WITHOUT firing propose_* tools.
      2. Next regular AG-UI turn → if the user confirms, the agent emits
         the matching `propose_*` HITL card normally.

    The coordinator's system prompt enforces this split — see
    `_agents_factory.py:instructions[FLUJO MULTIMODAL]`. The stream filter
    below relays only text chunks + tool-use phase hints + errors.
    """
    _ensure_known_agent(agent_id)
    try:
        user_id = _extract_user_id_from_jwt(request)
    except UnauthorizedError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=401)

    if not (text or "").strip():
        return JSONResponse({"detail": "text required"}, status_code=400)
    if len(text) > _MAX_USER_TEXT_CHARS:
        return JSONResponse(
            {
                "detail": (
                    f"text exceeds {_MAX_USER_TEXT_CHARS} characters "
                    f"(got {len(text)})"
                )
            },
            status_code=400,
        )
    if len(images) > _MAX_IMAGES_PER_CALL:
        return JSONResponse(
            {"detail": f"max {_MAX_IMAGES_PER_CALL} images per call"},
            status_code=400,
        )

    from agno.media import Image

    img_objs: list[Image] = []
    for f in images:
        if not f.content_type or f.content_type not in _ALLOWED_IMAGE_MIME:
            return JSONResponse(
                {"detail": f"unsupported image mime: {f.content_type}"},
                status_code=400,
            )
        data = await f.read()
        if len(data) > _MAX_IMAGE_BYTES:
            return JSONResponse(
                {
                    "detail": (
                        f"{f.filename or 'image'} exceeds "
                        f"{_MAX_IMAGE_BYTES // (1024 * 1024)} MB"
                    )
                },
                status_code=413,
            )
        img_objs.append(Image(content=data, mime_type=f.content_type))

    from src.agents.factory import get_universe_team

    team = get_universe_team()
    session_id = f"main-{user_id}"

    # --- Non-streaming branch (kept for tests and scripts) -----------------
    if not stream:
        try:
            result = await team.arun(
                input=text,
                images=img_objs if img_objs else None,
                user_id=str(user_id),
                session_id=session_id,
                stream=False,
            )
        except Exception as exc:  # noqa: BLE001
            from src.shared.metrics import agent_runs_total

            agent_runs_total.labels(
                agent="universe_coordinator", status="error"
            ).inc()
            logger.error(
                "agui_multimodal_failed", user_id=str(user_id), error=str(exc)
            )
            return JSONResponse(
                {"detail": f"agent error: {exc}"},
                status_code=500,
            )
        from src.shared.metrics import agent_runs_total, record_agent_tokens

        agent_runs_total.labels(
            agent="universe_coordinator", status="completed"
        ).inc()
        toks = record_agent_tokens(
            "universe_coordinator", getattr(result, "metrics", None)
        )
        logger.info("agui_multimodal_run", user_id=str(user_id), **toks)
        reply = getattr(result, "content", None)
        if not isinstance(reply, str):
            reply = str(reply) if reply is not None else ""
        run_id = getattr(result, "run_id", None)
        return JSONResponse({"response": reply, "run_id": run_id})

    # --- Streaming branch (default) ----------------------------------------
    async def event_stream():
        import json as _json

        try:
            agen = team.arun(
                input=text,
                images=img_objs if img_objs else None,
                user_id=str(user_id),
                session_id=session_id,
                stream=True,
                stream_events=True,
            )
            run_id: str | None = None
            async for event in agen:
                # Capture run_id from any event that exposes it.
                ev_run_id = getattr(event, "run_id", None)
                if ev_run_id and run_id is None:
                    run_id = ev_run_id

                # We relay 3 event flavours and skip the rest (reasoning,
                # memory, etc.) to keep the payload tight:
                #   RunContentEvent           → text chunks
                #   ToolCallStartedEvent      → "agent is using tool X" hint
                #   ToolCallCompletedEvent    → tool finished
                #   RunErrorEvent             → error frame
                # Note: external_execution tool calls (propose_*) intentionally
                # are NOT relayed; the multimodal turn is text-only by contract,
                # HITL cards happen in the follow-up regular AG-UI turn.
                event_name = type(event).__name__
                if event_name == "RunContentEvent":
                    delta = getattr(event, "content", None)
                    if isinstance(delta, str) and delta:
                        yield (
                            f"data: {_json.dumps({'type': 'chunk', 'content': delta})}\n\n"
                        )
                elif event_name in (
                    "ToolCallStartedEvent",
                    "RunToolCallStartedEvent",
                ):
                    tool_name = getattr(event, "tool_name", None) or getattr(
                        event, "name", None
                    )
                    if tool_name:
                        yield (
                            f"data: {_json.dumps({'type': 'tool-start', 'name': str(tool_name)})}\n\n"
                        )
                elif event_name in (
                    "ToolCallCompletedEvent",
                    "RunToolCallCompletedEvent",
                ):
                    tool_name = getattr(event, "tool_name", None) or getattr(
                        event, "name", None
                    )
                    if tool_name:
                        yield (
                            f"data: {_json.dumps({'type': 'tool-end', 'name': str(tool_name)})}\n\n"
                        )
                elif event_name == "RunErrorEvent":
                    msg = getattr(event, "content", "agent error")
                    yield (
                        f"data: {_json.dumps({'type': 'error', 'message': str(msg)})}\n\n"
                    )
                    return
            yield f"data: {_json.dumps({'type': 'done', 'run_id': run_id})}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield (
                f"data: {_json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Event-stream cleanup
# ---------------------------------------------------------------------------

# agno pauses a member for HITL by appending this notice to the streamed text.
# It's framework plumbing, not something the user should read — strip it.
_HITL_NOTICE_RE = re.compile(
    r"\s*Member '[^']+' requires human input before continuing\.?\s*"
)


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


async def _clean_event_stream(events: Any, encoder: EventEncoder):
    """Yield encoded AG-UI frames with two route-mode artefacts removed.

    In ``mode="route"`` agno streams the chosen member's reply AND then a
    team-level summary that simply re-states it — so the same text renders
    twice — and it leaks an internal "Member '…' requires human input…" notice
    into the member's final text. We buffer each text message (START→…→END),
    strip the notice, and drop a message whose (normalised) text was already
    emitted this run. Tool-call and run-lifecycle events pass through untouched
    so HITL cards (propose_*, present_widget, …) keep rendering.
    """
    from ag_ui.core import TextMessageContentEvent

    buffers: dict[str, dict[str, Any]] = {}
    emitted_concat = ""
    async for event in events:
        etype = getattr(event, "type", None)
        try:
            if etype == EventType.TEXT_MESSAGE_START:
                buffers[event.message_id] = {"start": event, "text": ""}
                continue
            if etype == EventType.TEXT_MESSAGE_CONTENT and event.message_id in buffers:
                buffers[event.message_id]["text"] += event.delta or ""
                continue
            if etype == EventType.TEXT_MESSAGE_END and event.message_id in buffers:
                buf = buffers.pop(event.message_id)
                cleaned = _HITL_NOTICE_RE.sub(" ", buf["text"]).strip()
                norm = _norm_text(cleaned)
                is_dup = len(norm) >= 24 and norm in emitted_concat
                # Always re-emit START/END so a tool call parented to this
                # message isn't orphaned; emit CONTENT only when it's real and
                # not a duplicate (empty/dup → no visible bubble).
                yield encoder.encode(buf["start"])
                if cleaned and not is_dup:
                    emitted_concat += norm
                    yield encoder.encode(
                        TextMessageContentEvent(
                            type=EventType.TEXT_MESSAGE_CONTENT,
                            message_id=buf["start"].message_id,
                            delta=cleaned,
                        )
                    )
                yield encoder.encode(event)
                continue
        except Exception:  # never let cleanup break the stream
            pass
        yield encoder.encode(event)
    # Defensive: flush any unterminated buffers.
    for buf in buffers.values():
        yield encoder.encode(buf["start"])


# ---------------------------------------------------------------------------
# Shared streaming core
# ---------------------------------------------------------------------------


async def _stream_chat(
    *, request: Request, run_body: dict[str, Any], guard_concurrency: bool = False
) -> StreamingResponse | JSONResponse:
    user_id = _extract_user_id_from_jwt(request)

    try:
        run_input = RunAgentInput.model_validate(run_body)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            {"detail": f"Invalid AG-UI payload: {exc}"}, status_code=400
        )

    # Hard cap on user-message length — prevents abuse where someone pipes
    # multiple megabytes into the LLM. Only the LAST message matters since
    # that's what the current turn is about; older ones are already
    # truncated by the sliding-window memory.
    for msg in reversed(run_input.messages or []):
        if getattr(msg, "role", None) == "user":
            content = getattr(msg, "content", None) or ""
            if isinstance(content, str) and len(content) > _MAX_USER_TEXT_CHARS:
                return JSONResponse(
                    {
                        "detail": (
                            f"user message exceeds {_MAX_USER_TEXT_CHARS} "
                            f"characters (got {len(content)})"
                        )
                    },
                    status_code=400,
                )
            break

    # Single-chat enforcement.
    enforced_thread_id = f"main-{user_id}"
    run_input.thread_id = enforced_thread_id  # type: ignore[assignment]
    run_input.forwarded_props = {
        **(run_input.forwarded_props or {}),
        "user_id": str(user_id),
    }

    # Per-user concurrency guard — bounds simultaneous agent RUNS only.
    # The long-lived `connect` SSE channel (guard_concurrency=False) must NOT
    # consume a slot, or a single open chat page (×2 under React StrictMode)
    # would exhaust the cap and 429 every turn.
    acquired = False
    if guard_concurrency:
        if not await _acquire_stream_slot(str(user_id)):
            return JSONResponse(
                {
                    "detail": (
                        "too many concurrent chat runs "
                        f"(max {_MAX_CONCURRENT_STREAMS_PER_USER})"
                    )
                },
                status_code=429,
            )
        acquired = True

    from src.agents.factory import get_universe_team

    team = get_universe_team()
    encoder = EventEncoder()

    async def event_stream():
        # `run_team` already wraps agent errors and yields a RunErrorEvent,
        # but encoding/transport can still raise. Guard the whole loop so a
        # mid-stream failure always reaches the client as a clean error
        # frame (generic message — never leak internals) and is logged
        # server-side with our structured logger. We also record run
        # volume / latency / status for observability (token spend for the
        # streaming path is read from agno_sessions by the cost benchmark).
        import time as _time

        from src.shared.metrics import agent_run_seconds, agent_runs_total

        started = _time.monotonic()
        status = "completed"
        try:
            async for frame in _clean_event_stream(run_team(team, run_input), encoder):
                yield frame
        except Exception as exc:  # noqa: BLE001
            status = "error"
            logger.error(
                "agui_stream_failed",
                user_id=str(user_id),
                thread_id=enforced_thread_id,
                error=str(exc),
                exc_info=True,
            )
            try:
                yield encoder.encode(
                    RunErrorEvent(
                        type=EventType.RUN_ERROR,
                        message="internal error",
                    )
                )
            except Exception:  # noqa: BLE001
                yield 'data: {"type":"RUN_ERROR","message":"internal error"}\n\n'
        finally:
            if acquired:
                await _release_stream_slot(str(user_id))
            agent_runs_total.labels(
                agent="universe_coordinator", status=status
            ).inc()
            agent_run_seconds.labels(agent="universe_coordinator").observe(
                _time.monotonic() - started
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _ensure_known_agent(agent_id: str) -> None:
    if agent_id not in _AGENT_DESCRIPTORS:
        # Don't 404 — CopilotKit caches agent IDs and a transient 404 makes
        # the React layer give up. Map any unknown id to the coordinator.
        return None
    return None


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
