"""Unit tests for entity_resolution pure helpers (no DB)."""
from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from src.coherence.application.entity_resolution import (
    MatchCandidate,
    PairwiseScore,
    ResolutionResult,
    _cluster_matches,
    _extract_date,
    _to_date,
    _to_number,
)


class TestClusterMatches:
    def test_empty_returns_empty(self):
        assert _cluster_matches([], 0.5) == []

    def test_single_pair_above_threshold(self):
        a, b = uuid4(), uuid4()
        clusters = _cluster_matches([(a, b, 0.9)], 0.5)
        assert len(clusters) == 1
        assert clusters[0].entity_ids == {a, b}

    def test_below_threshold_ignored(self):
        a, b = uuid4(), uuid4()
        clusters = _cluster_matches([(a, b, 0.3)], 0.5)
        assert clusters == []

    def test_transitive_cluster(self):
        a, b, c = uuid4(), uuid4(), uuid4()
        clusters = _cluster_matches([(a, b, 0.9), (b, c, 0.9)], 0.5)
        assert len(clusters) == 1
        assert clusters[0].entity_ids == {a, b, c}


class TestExtractDate:
    def test_none(self):
        assert _extract_date({}, "start_date") is None

    def test_date_object(self):
        d = date(2024, 1, 1)
        assert _extract_date({"start_date": d}, "start_date") == d

    def test_datetime_object(self):
        dt = datetime(2024, 1, 1, 12, 0)
        assert _extract_date({"start_date": dt}, "start_date") == date(2024, 1, 1)

    def test_iso_string(self):
        assert _extract_date({"start_date": "2024-01-15"}, "start_date") == date(2024, 1, 15)

    def test_invalid_string(self):
        assert _extract_date({"start_date": "nope"}, "start_date") is None

    def test_int_returns_none(self):
        assert _extract_date({"start_date": 2024}, "start_date") is None


class TestToDate:
    def test_none(self):
        assert _to_date(None) is None

    def test_date(self):
        d = date(2024, 1, 1)
        assert _to_date(d) == d

    def test_datetime(self):
        dt = datetime(2024, 1, 1, 12, 0)
        assert _to_date(dt) == date(2024, 1, 1)

    def test_iso_string(self):
        assert _to_date("2024-06-15") == date(2024, 6, 15)

    def test_invalid(self):
        assert _to_date("not-a-date") is None
        assert _to_date(123) is None


class TestToNumber:
    def test_none(self):
        assert _to_number(None) is None

    def test_int(self):
        assert _to_number(42) == 42.0

    def test_float(self):
        assert _to_number(3.14) == 3.14

    def test_string(self):
        assert _to_number("7.5") == 7.5

    def test_invalid(self):
        assert _to_number("nope") is None


class TestResolutionResult:
    def test_default_merged_ids(self):
        r = ResolutionResult(status="no_match", entity_id=None)
        assert r.merged_ids == []


class TestPairwiseScore:
    def test_defaults(self):
        s = PairwiseScore(composite=0.8)
        assert s.embedding == 0.0


class TestMatchCandidate:
    def test_signals_default(self):
        m = MatchCandidate(entity_id=uuid4(), score=0.5)
        assert m.signals == {}
