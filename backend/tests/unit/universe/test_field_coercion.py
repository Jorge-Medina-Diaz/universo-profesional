"""Type-driven field coercion for universe entities (pure, no DB).

JSON/importers carry typed values as strings; asyncpg rejects a str where a
date/int is expected (the "'str' has no attribute 'toordinal'" 500). These
guard the coercion applied on CREATE (`_Base.__post_init__`) and UPDATE
(`coerce_patch`, used by `_EntityCrud._apply_patch`) — covering EVERY date/int
field, not a hardcoded list (the gap that 500'd `started_on`/numeric fields).
"""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from src.shared.errors import ValidationError
from src.universe.domain.entities import (
    Course,
    Experience,
    Skill,
    coerce_patch,
)


def test_create_coerces_dates_and_numbers() -> None:
    c = Course.create(
        user_id=uuid4(),
        title="RAG in prod",
        started_on="2016-01-01",   # full ISO date
        completed_on="2016-07",     # partial (year-month) — common in CVs
        duration_hours="40",        # numeric-as-string
    )
    assert c.started_on == date(2016, 1, 1)
    assert c.completed_on == date(2016, 7, 1)
    assert c.duration_hours == 40 and isinstance(c.duration_hours, int)


def test_create_coerces_skill_integers() -> None:
    s = Skill.create(user_id=uuid4(), name="Python", years="5", last_used_year="2020")
    assert s.years == 5 and isinstance(s.years, int)
    assert s.last_used_year == 2020


def test_update_patch_coerces_dates_for_non_hardcoded_fields() -> None:
    # started_on is NOT in the legacy _DATE_FIELDS list — the type-driven path
    # must still coerce it (this is the field class that used to 500 on merge).
    out = coerce_patch(Course, {"started_on": "2016", "duration_hours": "12"})
    assert out["started_on"] == date(2016, 1, 1)
    assert out["duration_hours"] == 12


def test_update_patch_coerces_experience_partial_ranges() -> None:
    out = coerce_patch(Experience, {"start_date": "2022-07", "end_date": "2024-05"})
    assert out["start_date"] == date(2022, 7, 1)
    assert out["end_date"] == date(2024, 5, 1)


def test_coercion_is_idempotent_on_correct_types() -> None:
    d = date(2020, 5, 1)
    out = coerce_patch(Course, {"started_on": d, "duration_hours": 30})
    assert out["started_on"] is d
    assert out["duration_hours"] == 30


def test_unknown_and_string_fields_untouched() -> None:
    out = coerce_patch(Skill, {"name": "Rust", "category": "hard"})
    assert out == {"name": "Rust", "category": "hard"}


def test_blank_strings_become_none() -> None:
    out = coerce_patch(Course, {"started_on": "", "duration_hours": "  "})
    assert out["started_on"] is None
    assert out["duration_hours"] is None


def test_malformed_date_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        coerce_patch(Course, {"started_on": "not-a-date"})


def test_malformed_number_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        coerce_patch(Skill, {"years": "abc"})
