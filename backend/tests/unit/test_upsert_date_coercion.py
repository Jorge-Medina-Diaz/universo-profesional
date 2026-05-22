"""Partial-date coercion at the coherence write funnel (pure, no DB).

Agents emit year-only ('2023') or year-month ('2023-06') for DATE columns;
asyncpg needs a real date. These guard the coercion that prevents the
"'str' object has no attribute 'toordinal'" 500 on confirm.
"""
from __future__ import annotations

from datetime import date

from src.coherence.application.upsert_use_cases import (
    _coerce_date_fields,
    _parse_partial_date,
)


def test_year_only() -> None:
    assert _parse_partial_date("2023") == date(2023, 1, 1)


def test_year_month() -> None:
    assert _parse_partial_date("2023-06") == date(2023, 6, 1)


def test_full_iso() -> None:
    assert _parse_partial_date("2023-06-15") == date(2023, 6, 15)


def test_blank_and_garbage_become_none() -> None:
    assert _parse_partial_date("") is None
    assert _parse_partial_date("   ") is None
    assert _parse_partial_date("present") is None
    assert _parse_partial_date("n/a") is None


def test_coerce_only_touches_date_fields() -> None:
    payload = {
        "name": "AWS SAA",          # untouched
        "issued_on": "2023",        # → date
        "expires_on": "2026-03",    # → date
        "years": "5",               # NOT a date field → untouched
    }
    out = _coerce_date_fields(payload)
    assert out["name"] == "AWS SAA"
    assert out["issued_on"] == date(2023, 1, 1)
    assert out["expires_on"] == date(2026, 3, 1)
    assert out["years"] == "5"


def test_coerce_leaves_real_dates_untouched() -> None:
    d = date(2020, 5, 1)
    out = _coerce_date_fields({"start_date": d})
    assert out["start_date"] is d


def test_coerce_unparseable_date_becomes_none() -> None:
    out = _coerce_date_fields({"end_date": "presente"})
    assert out["end_date"] is None
