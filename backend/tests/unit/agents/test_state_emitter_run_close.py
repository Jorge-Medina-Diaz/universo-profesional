"""No state event may follow RUN_FINISHED / RUN_ERROR.

CopilotKit v1.57 hard-rejects a STATE_DELTA once the run is closed
("Cannot send event type 'STATE_DELTA': the run has already finished").
That rejection aborts the *client* run, and when it lands mid
TOOL_CALL_ARGS stream the proposal card renders with empty args — the
flagship generative-UI surface silently degrades to a blank card.

Agno keeps emitting after the run closes (post-turn auto-enrichment is the
usual source), so guarding only the RUN_FINISHED branch is not enough.
"""

from __future__ import annotations

import asyncio

from ag_ui.core import EventType
from src.agents.interfaces.state_emitter import emit_agent_state

_STATE_EVENTS = {EventType.STATE_DELTA, EventType.STATE_SNAPSHOT}


class _Evt:
    def __init__(self, type_, **kw):
        self.type = type_
        for k, v in kw.items():
            setattr(self, k, v)


async def _collect(events):
    async def gen():
        for e in events:
            yield e

    return [e async for e in emit_agent_state(gen(), {"_provider_intent": "expand_universe"})]


def _types_after_close(out):
    seen_close, after = False, []
    for e in out:
        t = getattr(e, "type", None)
        if seen_close:
            after.append(t)
        if t in (EventType.RUN_FINISHED, EventType.RUN_ERROR):
            seen_close = True
    return after


def test_no_state_events_after_run_finished() -> None:
    # agno keeps talking after RUN_FINISHED — the exact shape that broke cards.
    out = asyncio.run(_collect([
        _Evt(EventType.RUN_STARTED),
        _Evt(EventType.TOOL_CALL_START, tool_call_name="propose_experience", tool_call_id="t1"),
        _Evt(EventType.TOOL_CALL_ARGS, tool_call_id="t1", delta='{"role":"Prin'),
        _Evt(EventType.RUN_FINISHED),
        _Evt(EventType.TEXT_MESSAGE_CONTENT, delta="trailing enrichment chatter"),
        _Evt(EventType.TOOL_CALL_START, tool_call_name="universe_retrieve", tool_call_id="t2"),
        _Evt(EventType.TOOL_CALL_END, tool_call_id="t2"),
    ]))
    leaked = [t for t in _types_after_close(out) if t in _STATE_EVENTS]
    assert leaked == [], f"state events leaked after RUN_FINISHED: {leaked}"


def test_no_state_events_after_run_error() -> None:
    out = asyncio.run(_collect([
        _Evt(EventType.RUN_STARTED),
        _Evt(EventType.RUN_ERROR, message="boom"),
        _Evt(EventType.TEXT_MESSAGE_CONTENT, delta="late"),
    ]))
    leaked = [t for t in _types_after_close(out) if t in _STATE_EVENTS]
    assert leaked == [], f"state events leaked after RUN_ERROR: {leaked}"


def test_still_narrates_before_the_run_closes() -> None:
    """The guard must not silence normal in-run narration."""
    out = asyncio.run(_collect([
        _Evt(EventType.RUN_STARTED),
        _Evt(EventType.TOOL_CALL_START, tool_call_name="propose_experience", tool_call_id="t1"),
        _Evt(EventType.RUN_FINISHED),
    ]))
    kinds = [getattr(e, "type", None) for e in out]
    assert EventType.STATE_SNAPSHOT in kinds, "snapshot missing on RUN_STARTED"
    assert EventType.STATE_DELTA in kinds, "proposal delta missing before close"


if __name__ == "__main__":  # pragma: no cover - manual run
    test_no_state_events_after_run_finished()
    test_no_state_events_after_run_error()
    test_still_narrates_before_the_run_closes()
    print("ok")
