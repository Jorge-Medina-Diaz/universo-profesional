"""Structural guards for the coordinator team wiring.

These are NOT live-LLM routing tests (that needs an API key + the running
stack); they assert the *wiring* that routing depends on, so a refactor
can't silently drop a specialist, un-wire the graph retrieval tools, or
re-introduce a tool we deliberately removed from the coordinator.

Building the team is offline-safe: with no API key the provider resolves to
a mock model, and Agno creates its session schema lazily.
"""
from __future__ import annotations

from src.agents.factory import get_universe_team

# Every specialist the coordinator must be able to route to (P1.D roster).
EXPECTED_MEMBERS = {
    "entity_curator",
    "onboarding_specialist",
    "discovery_coach",
    "profile_analyst",
    "document_coach",
    "job_strategist",
    "domain_expert",
}

# Read-heavy specialists that must use the graph retriever (Sprint O wiring).
RETRIEVAL_WIRED = {
    "profile_analyst",
    "document_coach",
    "job_strategist",
    "domain_expert",
}

# The consolidation must not regress the FE card contract: every per-entity
# propose_* tool must still exist on the curator (the cards key off tool name).
CURATOR_PROPOSE_TOOLS = {
    "propose_experience",
    "propose_education",
    "propose_project",
    "propose_skill",
    "propose_skill_batch",
    "propose_certification",
    "propose_course",
    "propose_language",
    "propose_achievement",
    "propose_interest",
    "propose_artifact",
    "propose_entity",
}


def _tool_names(tools) -> set[str]:
    names: set[str] = set()
    for t in tools or []:
        name = getattr(t, "name", None) or getattr(t, "__name__", None)
        if name:
            names.add(str(name))
    return names


def test_all_specialists_are_members() -> None:
    team = get_universe_team()
    member_names = {m.name for m in team.members}
    missing = EXPECTED_MEMBERS - member_names
    assert not missing, f"coordinator missing specialists: {sorted(missing)}"
    extra = member_names - EXPECTED_MEMBERS
    assert not extra, f"unexpected members (roster creep): {sorted(extra)}"


def test_curator_keeps_every_propose_card_tool() -> None:
    team = get_universe_team()
    curator = next(m for m in team.members if m.name == "entity_curator")
    names = _tool_names(curator.tools)
    missing = CURATOR_PROPOSE_TOOLS - names
    assert not missing, f"entity_curator lost propose tools (breaks FE cards): {sorted(missing)}"


def test_coordinator_has_graph_retrieval_tools() -> None:
    team = get_universe_team()
    names = _tool_names(team.tools)
    for required in ("universe_retrieve", "get_graph_neighbors", "explain_path"):
        assert required in names, f"coordinator missing {required}; has {sorted(names)}"
    assert "present_graph_view" in names


def test_coordinator_dropped_redundant_tools() -> None:
    # These were removed: superseded by universe_retrieve, or already
    # injected as frontend readables. Re-adding them is a regression.
    team = get_universe_team()
    names = _tool_names(team.tools)
    for removed in (
        "search_universe",
        "list_jobs",
        "list_documents",
        "get_preferences",
        "list_reminders",
        "get_integrations_status",
        "get_tier",
    ):
        assert removed not in names, f"{removed} should not be on the coordinator"


def test_coordinator_has_tool_call_limit() -> None:
    team = get_universe_team()
    assert getattr(team, "tool_call_limit", None) == 12


def test_read_heavy_specialists_use_retrieval() -> None:
    team = get_universe_team()
    by_name = {m.name: m for m in team.members}
    for name in RETRIEVAL_WIRED:
        agent = by_name.get(name)
        assert agent is not None, f"{name} not found among members"
        assert "universe_retrieve" in _tool_names(agent.tools), (
            f"{name} should use universe_retrieve (Sprint O)"
        )
