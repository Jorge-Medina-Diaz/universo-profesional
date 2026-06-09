"""Offline routing eval — verifies the coordinator can reach every specialist.

This is an MVP "golden dataset" eval.  We cannot run live LLM calls in CI
(offline, no API key, deterministic), so we validate the structural pre-
conditions that routing depends on:

  1. Every expected specialist is a member of the Team.
  2. Each specialist owns the tools required for its golden-turn domain.
  3. The coordinator instructions contain the routing keywords that would
     steer a capable LLM to the correct member.

A future iteration can run the actual Team against a real model and assert
on the member name returned in the response metadata.
"""
from __future__ import annotations

import pytest
from src.agents.factory import STATIC_INSTRUCTIONS, get_universe_team

# ---------------------------------------------------------------------------
# Golden dataset: ~20 representative turns → expected specialist
# ---------------------------------------------------------------------------

GOLDEN_TURNS: list[dict[str, str]] = [
    # Single-entity capture (P1.D: all CRUD routes to the curator)
    {"input": "Trabajé en Google como Senior Backend 2020-2023", "specialist": "entity_curator"},
    {"input": "Sé React, TypeScript y Node.js", "specialist": "entity_curator"},
    {"input": "Tengo la certificación AWS Solutions Architect", "specialist": "entity_curator"},
    {"input": "Quiero apuntar una reflexión sobre mi carrera", "specialist": "entity_curator"},
    # Job search + interview prep (merged surface)
    {"input": "¿A qué ofertas debería aplicar esta semana?", "specialist": "job_strategist"},
    {"input": "Tengo una entrevista técnica mañana en Stripe", "specialist": "job_strategist"},
    # Documents (generation + coaching merged)
    {"input": "¿Qué plantilla de CV me conviene para una startup?", "specialist": "document_coach"},
    # Analysis (health / identity / portfolio / goals merged)
    {"input": "¿Cómo va mi perfil? ¿Qué me falta para senior?", "specialist": "profile_analyst"},
    {"input": "¿Qué tecnologías debería destacar para un rol de staff?", "specialist": "profile_analyst"},
    {"input": "Quiero ser tech lead en 6 meses", "specialist": "profile_analyst"},
    {"input": "¿Qué debería mostrar en mi portfolio para esta oferta?", "specialist": "profile_analyst"},
    # Discovery + active learning (merged)
    {"input": "Estoy aprendiendo LangGraph y montando un agente multi-tool", "specialist": "discovery_coach"},
    # Deep verticals (one expert)
    {"input": "Tengo un pipeline de dbt + Airflow + Snowflake en producción", "specialist": "domain_expert"},
    # Onboarding / batch ingest
    {"input": "Mi CV, experiencia y certificaciones", "specialist": "onboarding_specialist"},
]

# Specialist → minimum tool names that must be present for the golden turn.
_REQUIRED_TOOLS: dict[str, set[str]] = {
    "entity_curator": {
        "propose_experience",
        "propose_skill",
        "propose_skill_batch",
        "propose_certification",
        "propose_entity",
        "add_note",
        "find_existing",
        "mark_stale",
    },
    "job_strategist": {
        "propose_job_create",
        "list_jobs",
        "present_widget",
        "universe_retrieve",
        "get_interview_context_blob",
    },
    "document_coach": {
        "propose_cv_regenerate",
        "propose_document_generation",
        "list_documents",
        "compute_job_match",
    },
    "profile_analyst": {
        "compute_profile_health",
        "get_universe_summary",
        "get_universe_shape",
        "universe_retrieve",
        "propose_goal",
        "list_goals",
        "present_widget",
        "list_artifacts",
    },
    "discovery_coach": {
        "present_deep_dive",
        "add_learning_note",
        "suggest_discovery_questions",
        "get_profile_completeness",
    },
    "domain_expert": {
        "present_deep_dive",
        "propose_project",
        "propose_architecture_decision",
        "search_rubrics",
    },
    "onboarding_specialist": {"present_import_review", "get_universe_summary"},
}


@pytest.fixture(scope="module")
def team():
    return get_universe_team()


@pytest.fixture(scope="module")
def members_by_name(team):
    return {m.name: m for m in team.members}


@pytest.fixture(scope="module")
def coordinator_instructions_text():
    return " ".join(STATIC_INSTRUCTIONS)


def _tool_names(tools) -> set[str]:
    names: set[str] = set()
    for t in tools or []:
        name = getattr(t, "name", None) or getattr(t, "__name__", None)
        if name:
            names.add(str(name))
    return names


class TestRoutingWiring:
    """Structural pre-conditions for correct coordinator routing."""

    @pytest.mark.parametrize("turn", GOLDEN_TURNS, ids=lambda t: t["specialist"])
    def test_specialist_is_member(self, team, turn):
        member_names = {m.name for m in team.members}
        assert turn["specialist"] in member_names, (
            f"{turn['specialist']} missing from team members"
        )

    @pytest.mark.parametrize("turn", GOLDEN_TURNS, ids=lambda t: t["specialist"])
    def test_specialist_has_required_tools(self, members_by_name, turn):
        specialist = turn["specialist"]
        agent = members_by_name.get(specialist)
        assert agent is not None, f"{specialist} not found"
        required = _REQUIRED_TOOLS.get(specialist, set())
        if not required:
            pytest.skip(f"no required-tools declared for {specialist}")
        present = _tool_names(agent.tools)
        missing = required - present
        assert not missing, f"{specialist} missing tools: {sorted(missing)}"

    @pytest.mark.parametrize("turn", GOLDEN_TURNS, ids=lambda t: t["specialist"])
    def test_instructions_contain_routing_keyword(self, coordinator_instructions_text, turn):
        """The coordinator prompt must name the specialist so an LLM can route."""
        keyword = turn["specialist"]
        assert keyword in coordinator_instructions_text, (
            f"STATIC_INSTRUCTIONS do not mention '{keyword}' — routing would fail"
        )


class TestTeamFlagsV2:
    """Verify v2.6.9 flag migration replaced the deprecated mode="route"."""

    def test_respond_directly_is_true(self, team):
        assert getattr(team, "respond_directly", None) is True

    def test_determine_input_for_members_is_false(self, team):
        assert getattr(team, "determine_input_for_members", None) is False

    def test_share_member_interactions_is_true(self, team):
        assert getattr(team, "share_member_interactions", None) is True

    def test_add_team_history_to_members_is_true(self, team):
        assert getattr(team, "add_team_history_to_members", None) is True

    def test_mode_attribute_is_route_equivalent(self, team):
        # In v2.6.9 Agno derives an internal ``mode`` from the flag set.
        # When respond_directly=True the effective mode is still "route".
        mode = getattr(team, "mode", None)
        assert mode is not None, "team mode not set"
        mode_value = mode.value if hasattr(mode, "value") else str(mode)
        assert mode_value == "route", f"expected route-like mode, got {mode!r}"


class TestNativeMemory:
    """Agno v2.6.9 native memory flags."""

    def test_enable_session_summaries(self, team):
        assert getattr(team, "enable_session_summaries", None) is True

    def test_enable_user_memories(self, team):
        assert getattr(team, "enable_user_memories", None) is True


class TestGuardrails:
    """Guardrails attached to the coordinator Team."""

    def test_pre_hooks_present(self, team):
        hooks = getattr(team, "pre_hooks", None)
        assert hooks is not None, "pre_hooks missing from Team"
        hook_names = {type(h).__name__ for h in hooks}
        # PII detection is deliberately absent: a career-profile product's
        # legitimate content IS personal data (names, emails on CVs).
        assert "PromptInjectionGuardrail" in hook_names


class TestRetries:
    """Team-level retry configuration."""

    def test_retries_configured(self, team):
        assert getattr(team, "retries", 0) >= 1

    def test_exponential_backoff_enabled(self, team):
        assert getattr(team, "exponential_backoff", False) is True
