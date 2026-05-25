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
import uuid
from typing import Any

import structlog
from ag_ui.core import (
    EventType,
    RunAgentInput,
    RunErrorEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from ag_ui.encoder import EventEncoder
from fastapi import APIRouter, Body, Query, Request
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


# Cap on a single chat input (user message length).
_MAX_USER_TEXT_CHARS = 10_000


# ---------------------------------------------------------------------------
# Event-stream cleanup
# ---------------------------------------------------------------------------

# agno pauses a member for HITL by appending this notice to the streamed text.
# It's framework plumbing, not something the user should read — strip it.
_HITL_NOTICE_RE = re.compile(
    r"\s*Member '[^']+' requires human input before continuing\.?\s*"
)

# Shown in-thread when a real user turn produces no output (agno swallows some
# provider failures, e.g. "credit balance too low"). Surfaced as a normal
# assistant message so the user's own turn persists and the failure is visible.
_AGENT_UNAVAILABLE_MSG = (
    "⚠️ No pude responder ahora mismo: el servicio de IA no está disponible "
    "(puede haberse quedado sin crédito o haber superado su límite). "
    "Inténtalo de nuevo en unos minutos."
)


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


async def _clean_event_stream(
    events: Any, encoder: EventEncoder, *, flag_empty_run: bool = False
):
    """Yield encoded AG-UI frames with two route-mode artefacts removed.

    In ``mode="route"`` agno streams the chosen member's reply AND then a
    team-level summary that simply re-states it — so the same text renders
    twice — and it leaks an internal "Member '…' requires human input…" notice
    into the member's final text. We buffer each text message (START→…→END),
    strip the notice, and drop a message whose (normalised) text was already
    emitted this run. Tool-call and run-lifecycle events pass through untouched
    so HITL cards (propose_*, present_widget, …) keep rendering.

    When ``flag_empty_run`` is set (a real user turn, not the passive connect
    channel), we also guard against SILENT failures: agno swallows some provider
    errors (e.g. Anthropic "credit balance too low") and ends the run cleanly
    with no text and no tool call. A run that produced nothing is a failure from
    the user's point of view, so we inject a visible assistant message in-thread
    (keeping the user's own turn) before letting `RUN_FINISHED` through — the
    client must never see a dead-silent empty turn.
    """
    buffers: dict[str, dict[str, Any]] = {}
    emitted_concat = ""
    produced_output = False
    error_seen = False
    async for event in events:
        etype = getattr(event, "type", None)
        # A tool call (HITL card, present_widget, present_graph_view, …) counts
        # as real output even when there's no assistant text.
        if etype is not None and "TOOL_CALL" in str(etype):
            produced_output = True
        if etype == EventType.RUN_ERROR:
            error_seen = True
        # Intercept a real run that finished without producing anything: surface
        # a visible assistant message IN-THREAD (so the user's turn persists),
        # then fall through to let RUN_FINISHED close the run normally. We do NOT
        # emit RUN_ERROR here — that rolls back the optimistic user message.
        if (
            flag_empty_run
            and etype == EventType.RUN_FINISHED
            and not produced_output
            and not error_seen
        ):
            logger.error("agui_empty_run", reason="run finished with no output")
            mid = f"err-{uuid.uuid4().hex}"
            yield encoder.encode(
                TextMessageStartEvent(
                    type=EventType.TEXT_MESSAGE_START, message_id=mid, role="assistant"
                )
            )
            yield encoder.encode(
                TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=mid,
                    delta=_AGENT_UNAVAILABLE_MSG,
                )
            )
            yield encoder.encode(
                TextMessageEndEvent(type=EventType.TEXT_MESSAGE_END, message_id=mid)
            )
            produced_output = True
            # fall through → RUN_FINISHED is yielded at the bottom of the loop
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
                    produced_output = True
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
# Multimodal extraction — native CopilotKit attachments arrive as InputContent
# parts on the last user message. agno's stock `run_team` keeps only text, so we
# run the team ourselves to also pass images (and inline PDF text) to the model.
# ---------------------------------------------------------------------------

_MAX_RUN_IMAGES = 3
_MAX_PDF_CHARS = 8000


def _decode_data_value(value: str) -> bytes:
    """Decode an InputContentDataSource value (raw base64 or data: URL)."""
    import base64

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


def _extract_agui_images(messages: list[Any]) -> list[Any]:
    """Build agno Image objects from image InputContent parts (data or url)."""
    from agno.media import Image

    images: list[Any] = []
    for part in _last_user_parts(messages):
        if getattr(part, "type", None) != "image":
            continue
        source = getattr(part, "source", None)
        if source is None:
            continue
        value = getattr(source, "value", None)
        if not value:
            continue
        mime = getattr(source, "mime_type", None)
        stype = getattr(source, "type", None)
        try:
            if stype == "url":
                images.append(Image(url=value))
            else:  # "data" (base64)
                images.append(Image(content=_decode_data_value(value), mime_type=mime))
        except Exception:  # skip an unreadable attachment
            continue
        if len(images) >= _MAX_RUN_IMAGES:
            break
    return images


def _extract_agui_pdf_text(messages: list[Any]) -> str:
    """Inline-parse text from attached PDF document parts (best-effort)."""
    import io

    chunks: list[str] = []
    for part in _last_user_parts(messages):
        source = getattr(part, "source", None)
        if source is None:
            continue
        mime = getattr(source, "mime_type", None)
        is_pdf = getattr(part, "type", None) == "document" or mime == "application/pdf"
        if not is_pdf or getattr(source, "type", None) != "data":
            continue
        value = getattr(source, "value", None)
        if not value:
            continue
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(_decode_data_value(value)))
            text = "\n".join((pg.extract_text() or "") for pg in reader.pages).strip()
            if text:
                chunks.append("[Documento adjunto]\n" + text[:_MAX_PDF_CHARS])
        except Exception:  # skip an unreadable PDF
            continue
    return "\n\n".join(chunks)


async def _run_team_with_attachments(team: Any, run_input: RunAgentInput) -> Any:
    """Like agno's `run_team`, but also passes image attachments and inline PDF
    text to `team.arun`. (agno's stock extractor keeps text only.)"""
    from agno.os.interfaces.agui.utils import (
        async_stream_agno_response_as_agui_events,
        extract_agui_user_input,
        validate_agui_state,
    )

    run_id = run_input.run_id or str(uuid.uuid4())
    try:
        messages = run_input.messages or []
        user_input = extract_agui_user_input(messages)
        images = _extract_agui_images(messages)
        pdf_text = _extract_agui_pdf_text(messages)
        if pdf_text:
            user_input = f"{user_input}\n\n{pdf_text}".strip() if user_input else pdf_text

        yield RunStartedEvent(
            type=EventType.RUN_STARTED, thread_id=run_input.thread_id, run_id=run_id
        )

        user_id = None
        if run_input.forwarded_props and isinstance(run_input.forwarded_props, dict):
            user_id = run_input.forwarded_props.get("user_id")
        session_state = validate_agui_state(run_input.state, run_input.thread_id)

        response_stream = team.arun(
            input=user_input,
            images=images or None,
            session_id=run_input.thread_id,
            stream=True,
            stream_events=True,
            user_id=user_id,
            session_state=session_state,
            run_id=run_id,
        )
        async for event in async_stream_agno_response_as_agui_events(
            response_stream=response_stream, thread_id=run_input.thread_id, run_id=run_id
        ):
            yield event
    except Exception as exc:
        logger.error("agui_run_failed", error=str(exc), exc_info=True)
        yield RunErrorEvent(type=EventType.RUN_ERROR, message="internal error")


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

    # Only a real run with a user message should be flagged as a silent failure
    # when it produces nothing. The passive `connect` channel (and empty turns)
    # legitimately finish without output and must not be turned into an error.
    has_user_message = any(
        getattr(m, "role", None) == "user"
        and isinstance(getattr(m, "content", None), str)
        and getattr(m, "content", "").strip()
        for m in (run_input.messages or [])
    )
    flag_empty_run = guard_concurrency and has_user_message

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
            async for frame in _clean_event_stream(
                _run_team_with_attachments(team, run_input),
                encoder,
                flag_empty_run=flag_empty_run,
            ):
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
