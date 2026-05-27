"""Unit tests for the coherence merge rules.

Each rule must be pure (no IO) and idempotent: merging the same payload twice
should not produce a different plan. We assert the diffs are precise so the
DiffCard UI doesn't surface noise.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from src.coherence.domain.merge_rules import merge_for


def _existing(entity_type: str, **overrides):
    base = {
        "id": uuid4(),
        "user_id": uuid4(),
        "source": "agent_chat",
        "confidence": 1.0,
    }
    defaults = {
        "skill": {"name": "Python", "category": "hard", "level": "intermediate", "years": 5,
                  "last_used_year": 2025},
        "experience": {"organization": "Acme", "role": "Engineer", "start_date": "2020-01-01",
                       "end_date": None, "is_current": True, "description": None,
                       "highlights": [], "competences": []},
        "education": {"institution": "USE", "degree": "BSc", "field_of_study": "CS",
                      "start_date": "2018-09-01", "end_date": "2022-06-01",
                      "description": None, "highlights": []},
        "project": {"name": "ml-demo", "description": None, "role": None,
                    "project_type": "side", "tech_stack": ["Python"], "highlights": [],
                    "impact": None, "status": "active", "url": None},
        "certification": {"name": "AWS SA", "issuer": "AWS", "issued_on": "2024-01-01",
                          "expires_on": "2027-01-01", "credential_id": None,
                          "verification_url": None},
        "course": {"title": "RAG 101", "platform": "DeepLearning.AI",
                   "started_on": "2026-04-01", "completed_on": None,
                   "duration_hours": 5, "certificate_url": None},
        "language": {"code": "en", "name": "English", "level": "C1",
                     "certification": None},
        "achievement": {"title": "Best paper", "achieved_on": "2024-06-01",
                        "description": "OSDI", "context": "Anthropic", "evidence_url": None},
        "interest": {"name": "RAG", "description": "Started studying mid-2026"},
    }
    base.update(defaults[entity_type])
    base.update(overrides)
    return base


# --- Skill -----------------------------------------------------------------


def test_skill_years_takes_max():
    plan = merge_for("skill", _existing("skill", years=5), {"name": "Python", "years": 6})
    assert any(d.field == "years" and d.old == 5 and d.new == 6 for d in plan.diffs)


def test_skill_years_preserved_when_payload_lower():
    plan = merge_for("skill", _existing("skill", years=5), {"name": "Python", "years": 3})
    assert all(d.field != "years" for d in plan.diffs)


def test_skill_level_rank_takes_higher():
    plan = merge_for(
        "skill",
        _existing("skill", level="intermediate"),
        {"name": "Python", "level": "expert"},
    )
    assert any(d.field == "level" and d.new == "expert" for d in plan.diffs)


def test_skill_category_conflict_requires_confirmation():
    plan = merge_for(
        "skill",
        _existing("skill", category="hard"),
        {"name": "Python", "category": "soft"},
    )
    assert plan.needs_user_confirmation
    assert plan.suggestion_kind == "skill_category_conflict"


# evidence_refs was dropped in migration 0017 — skill→evidence relations
# are graph edges now, so the merge rule no longer unions a list field.


# --- Experience ------------------------------------------------------------


def test_experience_end_date_takes_max_and_flips_is_current():
    plan = merge_for(
        "experience",
        _existing("experience", end_date=None, is_current=True),
        {"organization": "Acme", "role": "Engineer", "end_date": "2025-12-31"},
    )
    diff_fields = {d.field for d in plan.diffs}
    assert "end_date" in diff_fields
    assert "is_current" in diff_fields
    assert plan.merged_payload["is_current"] is False


def test_experience_highlights_union():
    plan = merge_for(
        "experience",
        _existing("experience", highlights=["led migration"]),
        {
            "organization": "Acme",
            "role": "Engineer",
            "highlights": ["led migration", "scaled to 1M users"],
        },
    )
    merged = plan.merged_payload["highlights"]
    assert "led migration" in merged
    assert "scaled to 1M users" in merged


# --- Education -------------------------------------------------------------


def test_education_better_of_degree():
    plan = merge_for(
        "education",
        _existing("education", degree=None),
        {"institution": "USE", "degree": "BSc"},
    )
    assert any(d.field == "degree" and d.new == "BSc" for d in plan.diffs)


# --- Project ---------------------------------------------------------------


def test_project_tech_stack_union_and_status_newer_wins():
    plan = merge_for(
        "project",
        _existing("project", tech_stack=["Python"], status="active"),
        {"name": "ml-demo", "tech_stack": ["LlamaIndex"], "status": "shipped"},
    )
    merged_stack = plan.merged_payload["tech_stack"]
    assert "Python" in merged_stack and "LlamaIndex" in merged_stack
    assert plan.merged_payload["status"] == "shipped"


# --- Certification ---------------------------------------------------------


def test_certification_expires_on_takes_max():
    plan = merge_for(
        "certification",
        _existing("certification", expires_on="2027-01-01"),
        {"name": "AWS SA", "issuer": "AWS", "expires_on": "2028-01-01"},
    )
    assert any(d.field == "expires_on" for d in plan.diffs)


# --- Course ----------------------------------------------------------------


def test_course_completed_on_preserved_once_set():
    plan = merge_for(
        "course",
        _existing("course", completed_on="2026-05-01"),
        {"title": "RAG 101", "platform": "DeepLearning.AI", "completed_on": None},
    )
    # Existing completion stays, no diff.
    assert all(d.field != "completed_on" for d in plan.diffs)


# --- Language --------------------------------------------------------------


def test_language_level_takes_higher_cefr():
    plan = merge_for(
        "language",
        _existing("language", level="B2"),
        {"code": "en", "name": "English", "level": "C2"},
    )
    assert any(d.field == "level" and d.new == "C2" for d in plan.diffs)


# --- Achievement -----------------------------------------------------------


def test_achievement_description_only_overrides_when_existing_empty():
    plan = merge_for(
        "achievement",
        _existing("achievement", description="OSDI"),
        {"title": "Best paper", "achieved_on": "2024-06-01", "description": "OSDI 2024 paper"},
    )
    # existing was truthy → preserved
    assert all(d.field != "description" for d in plan.diffs)


# --- Interest --------------------------------------------------------------


def test_interest_description_concatenates_when_new_info():
    plan = merge_for(
        "interest",
        _existing("interest", description="Started studying mid-2026"),
        {"name": "RAG", "description": "Now reading Lewis et al."},
    )
    merged = plan.merged_payload["description"]
    assert "mid-2026" in merged and "Lewis" in merged


def test_interest_description_no_change_when_same():
    plan = merge_for(
        "interest",
        _existing("interest", description="Started studying mid-2026"),
        {"name": "RAG", "description": "Started studying mid-2026"},
    )
    assert all(d.field != "description" for d in plan.diffs)


# --- Generic ---------------------------------------------------------------


def test_unknown_entity_type_raises():
    with pytest.raises(ValueError):
        merge_for("unknown_type", {"id": uuid4()}, {})


def test_empty_payload_produces_no_diffs():
    plan = merge_for("skill", _existing("skill"), {"name": "Python"})
    assert plan.diffs == []
