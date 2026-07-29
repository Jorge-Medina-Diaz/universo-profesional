"""Unit tests for shape_service pure helpers."""
from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from src.universe.application.shape_service import (
    _confidence,
    _experience_years,
    _infer_shape,
    _months_since,
    primary_area_from_strengths,
)
from src.universe.domain.entities import AreaStrength


class TestInferShape:
    def test_none_when_empty(self):
        assert _infer_shape({}, []) == "none"
        assert _infer_shape({"backend": 0.5}, []) == "none"

    def test_I_shape(self):
        scores = {"backend": 0.8, "frontend": 0.1}
        assert _infer_shape(scores, ["backend"]) == "I"

    def test_T_shape(self):
        scores = {"backend": 0.5, "frontend": 0.3, "devops": 0.2}
        assert _infer_shape(scores, ["backend"]) == "T"

    def test_pi_shape(self):
        scores = {"backend": 0.5, "frontend": 0.4}
        assert _infer_shape(scores, ["backend", "frontend"]) == "π"

    def test_M_shape(self):
        scores = {"backend": 0.4, "frontend": 0.3, "devops": 0.2}
        assert _infer_shape(scores, ["backend", "frontend", "devops"]) == "M"


class TestConfidence:
    def test_zero_breadth(self):
        assert _confidence(0, None) == 0.0

    def test_positive_breadth(self):
        assert _confidence(1, None) > 0.0
        assert _confidence(4, None) > 0.0
        assert _confidence(10, None) > 0.0

    def test_recency_penalty(self):
        fresh = _confidence(4, 6)
        old = _confidence(4, 60)
        assert old < fresh

    def test_capped_at_one(self):
        assert _confidence(100, 0) == 1.0


class TestMonthsSince:
    def test_none_or_zero(self):
        assert _months_since(None) is None
        assert _months_since(0) is None
        assert _months_since(-1) is None

    def test_positive(self):
        now = datetime.now(UTC)
        result = _months_since(now.year - 1)
        assert result is not None
        assert result >= 11


class TestExperienceYears:
    def test_no_start(self):
        exp = SimpleNamespace(start_date=None, end_date=None)
        assert _experience_years(exp) == 0.0

    def test_with_dates(self):
        exp = SimpleNamespace(start_date=date(2020, 1, 1), end_date=date(2021, 1, 1))
        assert _experience_years(exp) == pytest.approx(1.0, 0.1)

    def test_current(self):
        exp = SimpleNamespace(start_date=date(2020, 1, 1), end_date=None)
        result = _experience_years(exp)
        assert result > 0.0

    def test_zero_or_negative_delta(self):
        exp = SimpleNamespace(start_date=date(2025, 1, 1), end_date=date(2020, 1, 1))
        assert _experience_years(exp) == 0.0


class TestPrimaryAreaFromStrengths:
    def test_empty(self):
        assert primary_area_from_strengths([]) == ("none", 0.0, None)

    def test_single(self):
        s = AreaStrength(id=uuid4(), user_id=uuid4(), area="backend", confidence=0.9)
        assert primary_area_from_strengths([s]) == ("backend", 0.9, None)

    def test_multiple(self):
        s1 = AreaStrength(id=uuid4(), user_id=uuid4(), area="backend", confidence=0.9)
        s2 = AreaStrength(id=uuid4(), user_id=uuid4(), area="frontend", confidence=0.7)
        assert primary_area_from_strengths([s1, s2]) == ("backend", 0.9, "frontend")
