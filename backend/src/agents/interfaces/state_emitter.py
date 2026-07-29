"""AG-UI shared-state emission (P2.A) — makes `useCoAgent` live.

agno emits no STATE_SNAPSHOT/STATE_DELTA events, so the frontend's agent
state was reconstructed from heuristics. This pipeline stage watches the
converted AG-UI event stream and narrates a small, versioned state object:

    {v, agent_status, current_intent, active_specialist, current_tool,
     pending_proposal}

Snapshot once after RUN_STARTED, then RFC-6902 deltas on transitions. Kept
deliberately tiny (<1 KB): the graph/working-set state already flows through
dedicated tools (control_graph / set_chat_focus); this object is the
*narration layer* (what is the agent doing right now), consumed by
useCoAgent / ThinkingSteps / the dock status chip.
"""
from __future__ import annotations

import json
from typing import Any

import structlog
from ag_ui.core import EventType, StateDeltaEvent, StateSnapshotEvent

logger = structlog.get_logger(__name__)

# Mirror of the factory roster — used to spot the routed member inside the
# delegate tool args without depending on agno's arg schema.
_MEMBER_NAMES = (
    "entity_curator",
    "onboarding_specialist",
    "discovery_coach",
    "profile_analyst",
    "document_coach",
    "job_strategist",
    "domain_expert",
)

_DELEGATE_TOOL = "delegate_task_to_member"

# Tools that pause the run for user confirmation (cards) — any propose_* plus
# the destructive confirm.
def _is_proposal_tool(name: str) -> bool:
    return name.startswith("propose_") or name == "confirm_destructive"


def _delta(*ops: tuple[str, Any]) -> StateDeltaEvent:
    return StateDeltaEvent(
        type=EventType.STATE_DELTA,
        delta=[{"op": "replace", "path": path, "value": value} for path, value in ops],
    )


def _on_tool_start(name: str) -> tuple[str, StateDeltaEvent]:
    """Map a starting tool call to (new status, the delta announcing it)."""
    if name == _DELEGATE_TOOL:
        return "routing", _delta(("/agent_status", "routing"))
    if _is_proposal_tool(name):
        return "awaiting_confirmation", _delta(
            ("/agent_status", "awaiting_confirmation"),
            ("/pending_proposal", name),
        )
    return "using_tool", _delta(
        ("/agent_status", "using_tool"),
        ("/current_tool", name),
    )


async def emit_agent_state(events: Any, intent_state: dict[str, Any] | None) -> Any:
    """Pass-through stage that injects STATE_SNAPSHOT/STATE_DELTA events."""
    status = "thinking"
    delegate_args: dict[str, str] = {}  # tool_call_id → accumulated args json
    tool_names: dict[str, str] = {}  # tool_call_id → tool name
    snapshot_sent = False
    run_closed = False

    async for event in events:
        etype = getattr(event, "type", None)
        yield event  # the underlying event always flows; state trails it

        # Once the run is closed, NO further state events may be emitted.
        # Guarding only the RUN_FINISHED branch is not enough: anything agno
        # emits afterwards (post-turn auto-enrichment is the usual source)
        # would still drive a status transition and yield a trailing
        # STATE_DELTA. CopilotKit v1.57 rejects that with "run has already
        # finished", which aborts the client run *mid tool-call-args stream* —
        # the proposal card then renders with empty args.
        if run_closed:
            continue
        if etype in (EventType.RUN_FINISHED, EventType.RUN_ERROR):
            run_closed = True
            continue

        try:
            if etype == EventType.RUN_STARTED and not snapshot_sent:
                snapshot_sent = True
                yield StateSnapshotEvent(
                    type=EventType.STATE_SNAPSHOT,
                    snapshot={
                        "v": 1,
                        "agent_status": status,
                        "current_intent": (intent_state or {}).get("_provider_intent"),
                        "active_specialist": None,
                        "current_tool": None,
                        "pending_proposal": None,
                    },
                )
                continue
            if not snapshot_sent:
                continue

            if etype == EventType.TOOL_CALL_START:
                name = getattr(event, "tool_call_name", None) or ""
                tcid = getattr(event, "tool_call_id", "") or ""
                tool_names[tcid] = name
                if name == _DELEGATE_TOOL:
                    delegate_args[tcid] = ""
                status, delta = _on_tool_start(name)
                yield delta
            elif etype == EventType.TOOL_CALL_ARGS:
                tcid = getattr(event, "tool_call_id", "") or ""
                if tcid in delegate_args:
                    delegate_args[tcid] += getattr(event, "delta", "") or ""
            elif etype == EventType.TOOL_CALL_END:
                tcid = getattr(event, "tool_call_id", "") or ""
                args = delegate_args.pop(tcid, None)
                if args is not None:
                    member = _find_member(args)
                    if member:
                        status = "working"
                        yield _delta(
                            ("/agent_status", status),
                            ("/active_specialist", member),
                        )
                elif tool_names.get(tcid) and not _is_proposal_tool(tool_names[tcid]):
                    yield _delta(("/current_tool", None))
            elif etype == EventType.TEXT_MESSAGE_CONTENT and status not in (
                "answering",
                "awaiting_confirmation",
            ):
                status = "answering"
                yield _delta(("/agent_status", status))
        except Exception:  # narration must never break the stream
            logger.warning("state_emitter_failed", exc_info=True)


def _find_member(args_json: str) -> str | None:
    """Locate the routed member name inside the delegate tool args.

    Tries a real JSON parse first (member/agent/member_id keys), falls back
    to a substring scan against the known roster — robust to agno arg-schema
    drift.
    """
    try:
        parsed = json.loads(args_json)
        for key in ("member_id", "member", "agent_name", "agent_id"):
            value = parsed.get(key)
            if isinstance(value, str) and value in _MEMBER_NAMES:
                return value
    except Exception:
        pass
    for name in _MEMBER_NAMES:
        if name in args_json:
            return name
    return None
