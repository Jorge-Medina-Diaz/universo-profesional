"""R13: _inject_proposal_metadata special-cases the generic propose_entity.

The generic tool carries `entity_type` + `payload` in its args (not the tool
name). A valid kind must mint a proposal whose stored entity_type/entity_data
come from those args; an INVALID kind (or missing payload) must NOT mint a
proposal (which would NOOP on confirm) and must surface a visible
`proposal_error` instead. Per-entity propose_* must keep deriving the kind from
the tool name. No Redis here — set_proposal is monkeypatched.
"""
from __future__ import annotations

import pytest

from src.agents.interfaces import agui_streaming as s


class _FakeTool:
    def __init__(self, tool_name, tool_args):
        self.tool_name = tool_name
        self.tool_args = tool_args


class _FakeEvent:
    def __init__(self, tools):
        self.tools = tools
        self.session_id = "thread-1"


@pytest.fixture
def recorded(monkeypatch):
    calls: list[dict] = []

    async def _fake_set_proposal(**kw):
        calls.append(kw)

    monkeypatch.setattr(s, "set_proposal", _fake_set_proposal)
    return calls


async def test_propose_entity_valid_kind_mints_proposal(recorded):
    tool = _FakeTool("propose_entity", {"entity_type": "skill", "payload": {"name": "Python", "level": "high"}})
    await s._inject_proposal_metadata(_FakeEvent([tool]), "u1")

    assert "proposal_id" in tool.tool_args
    assert "proposal_error" not in tool.tool_args
    assert tool.tool_args["entity_type"] == "skill"
    assert len(recorded) == 1
    # entity_data stored is the inner payload, NOT the whole args dict.
    assert recorded[0]["entity_type"] == "skill"
    assert recorded[0]["entity_data"] == {"name": "Python", "level": "high"}


async def test_propose_entity_invalid_kind_is_visible_error(recorded):
    tool = _FakeTool("propose_entity", {"entity_type": "widget", "payload": {"x": 1}})
    await s._inject_proposal_metadata(_FakeEvent([tool]), "u1")

    # No proposal minted, no silent NOOP — a visible error instead.
    assert "proposal_id" not in tool.tool_args
    assert "proposal_error" in tool.tool_args
    assert recorded == []


async def test_propose_entity_missing_payload_is_visible_error(recorded):
    tool = _FakeTool("propose_entity", {"entity_type": "skill"})
    await s._inject_proposal_metadata(_FakeEvent([tool]), "u1")

    assert "proposal_id" not in tool.tool_args
    assert "proposal_error" in tool.tool_args
    assert recorded == []


async def test_per_entity_propose_still_uses_tool_name(recorded):
    tool = _FakeTool("propose_skill", {"name": "Rust", "level": "high"})
    await s._inject_proposal_metadata(_FakeEvent([tool]), "u1")

    assert tool.tool_args["entity_type"] == "skill"
    assert tool.tool_args.get("proposal_id")
    assert len(recorded) == 1
    assert recorded[0]["entity_type"] == "skill"
    # Per-entity path stores the args themselves as the entity data.
    assert recorded[0]["entity_data"]["name"] == "Rust"
