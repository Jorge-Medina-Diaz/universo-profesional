"""SSE/streaming logic for AG-UI chat endpoints."""
from __future__ import annotations

import asyncio
import contextlib
import copy as _copy
import re
import time as _time
import uuid
from typing import Any
from uuid import UUID

import structlog
from ag_ui.core import (
    EventType,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from ag_ui.encoder import EventEncoder
from agno.os.interfaces.agui.utils import (
    async_stream_agno_response_as_agui_events,
    extract_agui_user_input,
    validate_agui_state,
)
from agno.run.agent import RunEvent as _RunEvent
from agno.run.agent import RunPausedEvent as _AgentRunPausedEvent
from agno.run.team import RunErrorEvent as _TeamRunErrorEvent
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.agents.context_providers import IntentRouter
from src.agents.factory import get_universe_team
from src.agents.infrastructure.proposal_store import set_proposal
from src.agents.interfaces.agui_core import (
    _MAX_CONCURRENT_STREAMS_PER_USER,
    _acquire_stream_slot,
    _background_tasks,
    _extract_user_id_from_jwt,
    _last_user_text,
    _norm_text,
    _release_stream_slot,
)
from src.agents.interfaces.agui_multimodal import (
    _extract_agui_images,
    _extract_agui_pdf_text,
)
from src.agents.interfaces.agui_postrun import (
    _enrich_universe_from_chat,
    _persist_agno_usage,
)
from src.shared.db import get_session_factory, set_rls_user
from src.shared.metrics import (
    agent_proposals_total,
    agent_run_seconds,
    agent_runs_total,
)

logger = structlog.get_logger(__name__)

# Cap on a single chat input (user message length).
_MAX_USER_TEXT_CHARS = 10_000

# agno pauses a member for HITL by appending this notice to the streamed text.
# It's framework plumbing, not something the user should read — strip it.
_HITL_NOTICE_RE = re.compile(
    r"\s*Member '[^']+' requires human input before continuing\.?\s*"
)

# agno also leaks an English status line when a run pauses for an
# external-execution tool (our HITL cards). Internal plumbing — strip it.
_EXTERNAL_EXEC_NOTICE_RE = re.compile(
    r"\s*I have tools to execute,? but (?:it|they) needs? external execution\.?\s*",
    re.IGNORECASE,
)

# Shown in-thread when a real user turn produces no output (agno swallows some
# provider failures, e.g. "credit balance too low"). Surfaced as a normal
# assistant message so the user's own turn persists and the failure is visible.
_AGENT_UNAVAILABLE_MSG = (
    "⚠️ No pude responder ahora mismo: el servicio de IA no está disponible "
    "(puede haberse quedado sin crédito o haber superado su límite). "
    "Inténtalo de nuevo en unos minutos."
)

# Single-entity HITL proposals: each gets a generated proposal_id injected into
# its args and resolves via POST /proposals/{id}/resolve -> coherence upsert,
# where entity_type = name.replace("propose_", "") must be a valid universe
# kind. (propose_skill_batch is deliberately excluded — it commits per-skill
# client-side via its own renderAndWaitForResponse card, not this path.)
_PROPOSAL_TOOLS = {
    "propose_experience",
    "propose_skill",
    "propose_project",
    "propose_education",
    "propose_certification",
    "propose_goal",
    "propose_course",
    "propose_language",
    "propose_achievement",
    "propose_interest",
    "propose_artifact",
    "propose_architecture_decision",
}


async def _inject_proposal_metadata(ev: Any, user_id: str | None) -> None:
    """Detect proposal tool calls, generate IDs, store in cache, inject into args.

    Mutates the event's tools in-place so the AG-UI converter forwards the
    enriched arguments to CopilotKit, which passes them to
    ``useCopilotAction(({ name: 'propose_experience', ... }))``.
    """
    tools = getattr(ev, "tools", None) or []
    for tool in tools:
        name = getattr(tool, "tool_name", None)
        if name not in _PROPOSAL_TOOLS:
            continue
        args = getattr(tool, "tool_args", None) or {}
        if not isinstance(args, dict):
            continue

        proposal_id = str(uuid.uuid4())
        entity_type = name.replace("propose_", "")

        await set_proposal(
            user_id=user_id or "anonymous",
            proposal_id=proposal_id,
            entity_type=entity_type,
            entity_data=dict(args),
            action="create",
            confidence=0.85,
            reason="Propuesta generada por el agente",
            thread_id=getattr(ev, "session_id", None),
        )

        args["proposal_id"] = proposal_id
        args["entity_type"] = entity_type
        args["action"] = "create"
        args["confidence"] = 0.85
        args["reason"] = "Propuesta generada por el agente"
        agent_proposals_total.labels(entity_type=entity_type, action="create").inc()


async def _adapt_team_pause(ev: Any, user_id: str | None = None) -> Any:
    """Convert a TEAM-level RunPausedEvent into an AGENT-level one.

    This is a controlled workaround for Agno's AG-UI converter, which
    recognises `agent.RunPausedEvent` but not `team.RunPausedEvent`.
    Instead of mutating the event inline inside the streaming loop, we
    isolate the fragile `__class__` swap here so failures can be caught
    and surfaced as a proper `RunErrorEvent`.
    """
    if not getattr(ev, "is_paused", False):
        return ev
    if isinstance(ev, _AgentRunPausedEvent):
        await _inject_proposal_metadata(ev, user_id)
        return ev

    has_ext = any(
        getattr(t, "external_execution_required", False)
        for t in (getattr(ev, "tools", None) or [])
    )
    if not has_ext:
        return ev

    # The actual monkey-patch: copy + re-tag so the AG-UI converter routes
    # the pause and exposes `tools_awaiting_external_execution`.
    conv = _copy.copy(ev)
    conv.__class__ = _AgentRunPausedEvent
    conv.event = _RunEvent.run_paused
    conv.content = None  # drop "Team run paused…" plumbing text
    await _inject_proposal_metadata(conv, user_id)
    return conv


async def _surface_team_external_tools(
    raw: Any, user_id: str | None = None
) -> Any:
    """Make TEAM-level external-execution pauses visible to agno's AG-UI converter.

    Wraps the fragile `_adapt_team_pause` monkey-patch in a hard try/except
    boundary.  If the workaround itself breaks (e.g. Agno changes the
    dataclass layout in a future release) we emit a `RunErrorEvent` so the
    client sees a failure instead of a silent empty turn.
    """
    async for ev in raw:
        try:
            adapted = await _adapt_team_pause(ev, user_id=user_id)
        except Exception as exc:
            logger.error(
                "agui_team_pause_adapter_failed",
                error=str(exc),
                exc_info=True,
            )
            yield _TeamRunErrorEvent(
                event="run_error",
                error="Team pause adapter failed — please retry",
            )
            return
        yield adapted


async def _run_team_with_attachments(team: Any, run_input: RunAgentInput) -> Any:
    """Like agno's `run_team`, but also passes image attachments and inline PDF
    text to `team.arun`. (agno's stock extractor keeps text only.)"""
    run_id = run_input.run_id or str(uuid.uuid4())
    try:
        messages = run_input.messages or []
        user_input = extract_agui_user_input(messages)
        images = _extract_agui_images(messages)
        pdf_text = await _extract_agui_pdf_text(messages)
        if pdf_text:
            user_input = f"{user_input}\n\n{pdf_text}".strip() if user_input else pdf_text

        yield RunStartedEvent(
            type=EventType.RUN_STARTED, thread_id=run_input.thread_id, run_id=run_id
        )

        user_id = None
        if run_input.forwarded_props and isinstance(run_input.forwarded_props, dict):
            user_id = run_input.forwarded_props.get("user_id")
        session_state = validate_agui_state(run_input.state, run_input.thread_id)

        # Sprint R: Intent Router — classify user message and enrich session_state
        # with provider context so tools can adapt behaviour downstream.
        if user_id and user_input:
            try:
                factory = get_session_factory()
                async with factory() as db_session:
                    await set_rls_user(db_session, UUID(str(user_id)))
                    router = IntentRouter(db_session, UUID(str(user_id)))
                    intent = await router.classify(user_input)
                    provider = await router.get_provider(intent)
                    memory_ctx = await provider.get_memory_context()
                    session_state["_provider_intent"] = intent.name
                    session_state["_provider_name"] = intent.provider_name
                    session_state["_provider_confidence"] = intent.confidence
                    session_state["_provider_memory_context"] = memory_ctx
                    logger.info(
                        "intent_routed",
                        user_id=str(user_id),
                        intent=intent.name,
                        provider=intent.provider_name,
                        confidence=intent.confidence,
                    )
            except Exception as exc:
                logger.warning("intent_router_failed", error=str(exc), user_id=str(user_id))

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
            response_stream=_surface_team_external_tools(
                response_stream, user_id=user_id
            ),
            thread_id=run_input.thread_id,
            run_id=run_id,
        ):
            yield event
    except Exception as exc:
        logger.error("agui_run_failed", error=str(exc), exc_info=True)
        yield RunErrorEvent(type=EventType.RUN_ERROR, message="internal error")
        yield RunFinishedEvent(type=EventType.RUN_FINISHED, thread_id=run_input.thread_id, run_id=run_id)


async def _clean_event_stream(
    events: Any, encoder: EventEncoder, *, flag_empty_run: bool = False
):
    """Yield encoded AG-UI frames with two route-mode artefacts removed.

    With ``respond_directly=True`` (v2 flags) agno streams the chosen member's
    reply AND then a team-level summary that simply re-states it — so the same
    text renders twice — and it leaks an internal "Member '…' requires human
    input…" notice into the member's final text. We buffer each text message
    (START→…→END), strip the notice, and drop a message whose (normalised) text
    was already emitted this run. Tool-call and run-lifecycle events pass
    through untouched so HITL cards (propose_*, present_widget, …) keep
    rendering.

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
                cleaned = _HITL_NOTICE_RE.sub(" ", buf["text"])
                cleaned = _EXTERNAL_EXEC_NOTICE_RE.sub(" ", cleaned).strip()
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
    # Defensive: flush any unterminated buffers with a proper START + CONTENT +
    # END sequence. Emitting START alone left the message bubble permanently
    # open (CopilotKit shows a never-ending spinner).
    for buf in buffers.values():
        mid = buf["start"].message_id
        yield encoder.encode(buf["start"])
        cleaned = _HITL_NOTICE_RE.sub(" ", buf["text"])
        cleaned = _EXTERNAL_EXEC_NOTICE_RE.sub(" ", cleaned).strip()
        if cleaned:
            yield encoder.encode(
                TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=mid,
                    delta=cleaned,
                )
            )
        yield encoder.encode(
            TextMessageEndEvent(type=EventType.TEXT_MESSAGE_END, message_id=mid)
        )


async def _stream_chat(
    *, request: Request, run_body: dict[str, Any], guard_concurrency: bool = False
) -> StreamingResponse | JSONResponse:
    user_id = _extract_user_id_from_jwt(request)

    try:
        run_input = RunAgentInput.model_validate(run_body)
    except Exception as exc:
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
    run_input.thread_id = enforced_thread_id
    run_input.forwarded_props = {
        **(run_input.forwarded_props or {}),
        "user_id": str(user_id),
    }

    # PASSIVE CONNECT CHANNEL — never execute the team, never emit run events.
    #
    # CopilotKit opens `agent/connect` (guard_concurrency=False) on every mount /
    # reconnect / StrictMode pass to REPLAY an existing thread, not to generate
    # (see @copilotkit/core: "connectAgent … to replay historical messages for an
    # existing thread"). It reopens this channel many times per session.
    #
    # Two failure modes we must avoid:
    #   1. Running the team here → the coordinator "replies" to the loaded history
    #      (phantom turns that look like the user wrote them) and re-emits an open
    #      `propose_*` proposal on every reconnect (the confirm-loop).
    #   2. Emitting RUN_STARTED/RUN_FINISHED here → each reconnect starts a NEW
    #      run lifecycle on the client, which ABANDONS the paused HITL run and
    #      makes an open confirmation card vanish.
    #
    # So connect must be an inert channel: stream zero events and close. The
    # client keeps its in-memory messages (incl. any pending HITL card), and
    # scroll-back history is served separately by GET /threads/{id}/messages.
    # Only the active `/run` path (guard_concurrency=True) generates.
    if not guard_concurrency:
        async def passive_stream():
            # Empty async generator: no run-lifecycle events, immediate close.
            return
            yield  # pragma: no cover — marks this a generator

        return StreamingResponse(
            passive_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Per-user concurrency guard — bounds simultaneous agent RUNS only.
    # The long-lived `connect` SSE channel (guard_concurrency=False) must NOT
    # consume a slot, or a single open chat page (x2 under React StrictMode)
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

    team = get_universe_team()
    encoder = EventEncoder()

    return StreamingResponse(
        _event_stream(
            team=team,
            run_input=run_input,
            encoder=encoder,
            flag_empty_run=flag_empty_run,
            user_id=str(user_id),
            enforced_thread_id=enforced_thread_id,
            acquired=acquired,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _event_stream(
    *,
    team: Any,
    run_input: RunAgentInput,
    encoder: EventEncoder,
    flag_empty_run: bool,
    user_id: str,
    enforced_thread_id: str,
    acquired: bool,
):
    """Yield encoded AG-UI frames for a single agent run.

    Guarded so a mid-stream failure always reaches the client as a clean
    error frame.  Also records run volume / latency / status.
    """
    started = _time.monotonic()
    status = "completed"
    try:
        async for frame in _clean_event_stream(
            _run_team_with_attachments(team, run_input),
            encoder,
            flag_empty_run=flag_empty_run,
        ):
            yield frame
    except Exception as exc:
        status = "error"
        logger.error(
            "agui_stream_failed",
            user_id=user_id,
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
        except Exception:
            yield 'data: {"type":"RUN_ERROR","message":"internal error"}\n\n'
        # Close the run as well: CopilotKit v1.57 leaves the client stuck in a
        # permanently-"running" state if RUN_ERROR is not followed by
        # RUN_FINISHED. Wrapped in its own guard so it can never break the SSE.
        try:
            yield encoder.encode(
                RunFinishedEvent(
                    type=EventType.RUN_FINISHED,
                    thread_id=enforced_thread_id,
                    run_id=run_input.run_id or "",
                )
            )
        except Exception:
            pass
    finally:
        if acquired:
            await _release_stream_slot(user_id)
        agent_runs_total.labels(
            agent="universe_coordinator", status=status
        ).inc()
        agent_run_seconds.labels(agent="universe_coordinator").observe(
            _time.monotonic() - started
        )
        # Post-run usage tracking — fire-and-forget so we never block the stream.
        with contextlib.suppress(Exception):
            _background_tasks.add(
                asyncio.create_task(_persist_agno_usage(enforced_thread_id, user_id))
            )
        # Post-run universe enrichment — every user message is a potential
        # source of new professional knowledge. Fire-and-forget so the SSE
        # closes immediately for the client.
        with contextlib.suppress(Exception):
            user_text = _last_user_text(run_input.messages)
            if user_text:
                _background_tasks.add(
                    asyncio.create_task(
                        _enrich_universe_from_chat(
                            user_id=user_id,
                            text=user_text,
                            thread_id=enforced_thread_id,
                        )
                    )
                )
