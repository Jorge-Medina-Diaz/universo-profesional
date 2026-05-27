"""Unit tests for entity_resolution pure helpers (no DB)."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

import pytest

from src.coherence.application.entity_resolution import (
    Cluster,
    MatchCandidate,
    PairwiseScore,
    ResolutionResult,
    _apply_field_rules,
    _cluster_matches,
    _extract_date,
    _resolve_concatenate_unique,
    _resolve_earliest,
    _resolve_esco_preferred,
    _resolve_field,
    _resolve_latest,
    _resolve_longest_non_null,
    _resolve_max,
    _resolve_max_ranked,
    _resolve_preserve_existing,
    _resolve_union,
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


class TestApplyFieldRules:
    def test_empty_rows(self):
        from src.coherence.domain.er_rules import FieldRule

        result = _apply_field_rules((FieldRule(field="name", strategy="longest_non_null"),), [])
        assert result == {}

    def test_longest_non_null(self):
        from src.coherence.domain.er_rules import FieldRule

        rules = (FieldRule(field="name", strategy="longest_non_null"),)
        rows = [{"name": "Py"}, {"name": "Python"}]
        result = _apply_field_rules(rules, rows)
        assert result["name"] == "Python"


class TestResolveStrategies:
    def test_longest_non_null(self):
        assert _resolve_longest_non_null(["aa", "bbb", "c"], None) == "bbb"

    def test_earliest(self):
        assert _resolve_earliest([date(2024, 1, 1), date(2023, 6, 1)], None) == date(2023, 6, 1)

    def test_earliest_fallback_to_first(self):
        assert _resolve_earliest(["not-a-date"], None) == "not-a-date"

    def test_latest(self):
        assert _resolve_latest([date(2024, 1, 1), date(2023, 6, 1)], None) == date(2024, 1, 1)

    def test_max(self):
        assert _resolve_max([3, 7, 2], None) == 7.0

    def test_max_ranked(self):
        assert _resolve_max_ranked(["basic", "expert"], {"basic": 1, "expert": 4}) == "expert"

    def test_max_ranked_raises_without_ranking(self):
        with pytest.raises(ValueError):
            _resolve_max_ranked(["a", "b"], None)

    def test_union(self):
        assert _resolve_union([["a", "b"], ["b", "c"]], None) == ["a", "b", "c"]

    def test_union_scalar(self):
        assert _resolve_union(["a", "b"], None) == ["a", "b"]

    def test_esco_preferred(self):
        assert _resolve_esco_preferred(["short", "much longer text"], None) == "much longer text"

    def test_concatenate_unique(self):
        assert _resolve_concatenate_unique(["hello", "world"], None) == "hello\n\nworld"

    def test_concatenate_unique_dedupes(self):
        assert _resolve_concatenate_unique(["hello", "hello"], None) == "hello"

    def test_preserve_existing(self):
        assert _resolve_preserve_existing(["first", "second"], None) == "first"


class TestResolveField:
    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError):
            _resolve_field("no_such_strategy", ["a"], None)


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
