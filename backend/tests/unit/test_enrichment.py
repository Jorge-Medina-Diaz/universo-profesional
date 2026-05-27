"""Unit tests for enrichment pure helpers."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from src.universe.application.enrichment import (
    EnrichmentStats,
    _date_overlap,
    _norm,
    _vec,
)


class TestNorm:
    def test_lowercases_and_strips(self):
        assert _norm("  Python  ") == "python"

    def test_none(self):
        assert _norm(None) == "none"


class TestVec:
    def test_none(self):
        assert _vec(None) is None

    def test_valid_list(self):
        assert _vec([1.0, 2.0]) == [1.0, 2.0]

    def test_invalid(self):
        assert _vec("not a vec") is None

    def test_empty_returns_none(self):
        assert _vec([]) is None


class TestDateOverlap:
    def test_no_overlap_when_no_start(self):
        p = SimpleNamespace(start_date=None, end_date=None, is_current=False)
        e = SimpleNamespace(start_date=date(2020, 1, 1), end_date=None, is_current=True)
        assert _date_overlap(p, e) is False

    def test_overlap(self):
        p = SimpleNamespace(start_date=date(2020, 1, 1), end_date=date(2021, 1, 1), is_current=False)
        e = SimpleNamespace(start_date=date(2020, 6, 1), end_date=None, is_current=True)
        assert _date_overlap(p, e) is True

    def test_no_overlap(self):
        p = SimpleNamespace(start_date=date(2020, 1, 1), end_date=date(2020, 6, 1), is_current=False)
        e = SimpleNamespace(start_date=date(2021, 1, 1), end_date=None, is_current=True)
        assert _date_overlap(p, e) is False


class TestEnrichmentStats:
    def test_as_dict(self):
        s = EnrichmentStats(related_to=5, uses_tech=3)
        assert s.as_dict() == {
            "embeddings_computed": 0,
            "related_to": 5,
            "uses_tech": 3,
            "part_of": 0,
            "communities": 0,
        }
