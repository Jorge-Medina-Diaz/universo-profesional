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

# Every specialist the coordinator must be able to route to.
EXPECTED_MEMBERS = {
    "experience_specialist",
    "education_specialist",
    "project_specialist",
    "skill_specialist",
    "certification_specialist",
    "course_specialist",
    "language_specialist",
    "achievement_specialist",
    "interest_specialist",
    "note_specialist",
    "job_strategist",
    "cv_coach",
    "curiosity_specialist",
    "goals_specialist",
    "insights_specialist",
    "interview_prep_specialist",
    "onboarding_specialist",
    "agent_system_specialist",
    "tech_radar_specialist",
    "cloud_posture_specialist",
    "data_engineering_specialist",
    "security_posture_specialist",
    "architecture_specialist",
    "portfolio_specialist",
}

# Read-heavy specialists that must use the graph retriever (Sprint O wiring).
RETRIEVAL_WIRED = {
    "cv_coach",
    "insights_specialist",
    "portfolio_specialist",
    "tech_radar_specialist",
    "interview_prep_specialist",
    "agent_system_specialist",
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
