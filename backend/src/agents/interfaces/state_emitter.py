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


async def emit_agent_state(events: Any, intent_state: dict[str, Any] | None) -> Any:
    """Pass-through stage that injects STATE_SNAPSHOT/STATE_DELTA events."""
    status = "thinking"
    delegate_args: dict[str, str] = {}  # tool_call_id → accumulated args json
    tool_names: dict[str, str] = {}  # tool_call_id → tool name
    snapshot_sent = False

    async for event in events:
        etype = getattr(event, "type", None)
        yield event  # the underlying event always flows; state trails it

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
                    status = "routing"
                    yield _delta(("/agent_status", status))
                elif _is_proposal_tool(name):
                    status = "awaiting_confirmation"
                    yield _delta(
                        ("/agent_status", status),
                        ("/pending_proposal", name),
                    )
                else:
                    status = "using_tool"
                    yield _delta(
                        ("/agent_status", status),
                        ("/current_tool", name),
                    )
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
            elif etype == EventType.RUN_FINISHED:
                yield _delta(("/agent_status", "idle"), ("/current_tool", None))
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
