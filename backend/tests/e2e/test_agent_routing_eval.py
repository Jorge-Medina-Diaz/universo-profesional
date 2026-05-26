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
    # Entity CRUD (10)
    {"input": "Trabajé en Google como Senior Backend 2020-2023", "specialist": "experience_specialist"},
    {"input": "Estudié Ingeniería Informática en la UPM", "specialist": "education_specialist"},
    {"input": "Monté un proyecto personal de scraping con Python", "specialist": "project_specialist"},
    {"input": "Sé React, TypeScript y Node.js", "specialist": "skill_specialist"},
    {"input": "Tengo la certificación AWS Solutions Architect", "specialist": "certification_specialist"},
    {"input": "Hice un curso de Machine Learning en Coursera", "specialist": "course_specialist"},
    {"input": "Hablo inglés nivel C1 y español nativo", "specialist": "language_specialist"},
    {"input": "Gané un hackathon en 2022", "specialist": "achievement_specialist"},
    {"input": "Me interesa la inteligencia artificial aplicada a salud", "specialist": "interest_specialist"},
    {"input": "Quiero apuntar una reflexión sobre mi carrera", "specialist": "note_specialist"},
    # Advisory (6)
    {"input": "¿A qué ofertas debería aplicar esta semana?", "specialist": "job_strategist"},
    {"input": "¿Qué plantilla de CV me conviene para una startup?", "specialist": "cv_coach"},
    {"input": "Tengo una entrevista técnica mañana en Stripe", "specialist": "interview_prep_specialist"},
    {"input": "¿Cómo va mi perfil? ¿Qué me falta para senior?", "specialist": "insights_specialist"},
    {"input": "¿Qué tecnologías debería destacar para un rol de staff?", "specialist": "tech_radar_specialist"},
    {"input": "Quiero ser tech lead en 6 meses", "specialist": "goals_specialist"},
    # Verticals + onboarding + portfolio (4)
    {"input": "Estoy aprendiendo LangGraph y montando un agente multi-tool", "specialist": "curiosity_specialist"},
    {"input": "Tengo un pipeline de dbt + Airflow + Snowflake en producción", "specialist": "data_engineering_specialist"},
    {"input": "Mi CV, experiencia y certificaciones", "specialist": "onboarding_specialist"},
    {"input": "¿Qué debería mostrar en mi portfolio para esta oferta?", "specialist": "portfolio_specialist"},
]

# Specialist → minimum tool names that must be present for the golden turn.
_REQUIRED_TOOLS: dict[str, set[str]] = {
    "experience_specialist": {"propose_experience", "upsert_experience"},
    "education_specialist": {"propose_education", "upsert_education"},
    "project_specialist": {"propose_project", "upsert_project"},
    "skill_specialist": {"propose_skill", "upsert_skill"},
    "certification_specialist": {"propose_certification", "upsert_certification"},
    "course_specialist": {"propose_course", "upsert_course"},
    "language_specialist": {"propose_language", "upsert_language"},
    "achievement_specialist": {"propose_achievement", "upsert_achievement"},
    "interest_specialist": {"propose_interest", "upsert_interest"},
    "note_specialist": {"add_note", "update_note"},
    "job_strategist": {"propose_job_create", "list_jobs"},
    "cv_coach": {"propose_cv_regenerate", "list_documents"},
    "interview_prep_specialist": {"present_widget", "universe_retrieve"},
    "insights_specialist": {"compute_profile_health", "get_universe_summary"},
    "tech_radar_specialist": {"get_universe_shape", "universe_retrieve"},
    "goals_specialist": {"propose_goal", "list_goals"},
    "curiosity_specialist": {"present_deep_dive", "add_learning_note"},
    "data_engineering_specialist": {"present_deep_dive", "upsert_project"},
    "onboarding_specialist": {"present_import_review", "get_universe_summary"},
    "portfolio_specialist": {"get_universe_summary", "present_widget"},
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
        assert "PIIDetectionGuardrail" in hook_names
        assert "PromptInjectionGuardrail" in hook_names


class TestRetries:
    """Team-level retry configuration."""

    def test_retries_configured(self, team):
        assert getattr(team, "retries", 0) >= 1

    def test_exponential_backoff_enabled(self, team):
        assert getattr(team, "exponential_backoff", False) is True
