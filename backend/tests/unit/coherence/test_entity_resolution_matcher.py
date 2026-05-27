"""Unit tests for PairwiseMatcher pure methods (no DB)."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from src.coherence.application.entity_resolution import PairwiseMatcher


class TestStringSim:
    def test_no_name_field(self):
        m = PairwiseMatcher.__new__(PairwiseMatcher)
        assert m._string_sim({}, {}, {"name_field": None}) == 0.0

    def test_empty_name(self):
        m = PairwiseMatcher.__new__(PairwiseMatcher)
        assert m._string_sim({"name": ""}, {"name": "X"}, {"name_field": "name"}) == 0.0

    def test_exact_match(self):
        m = PairwiseMatcher.__new__(PairwiseMatcher)
        assert m._string_sim({"name": "Python"}, {"name": "Python"}, {"name_field": "name"}) == 1.0

    def test_similar(self):
        m = PairwiseMatcher.__new__(PairwiseMatcher)
        score = m._string_sim({"name": "Python"}, {"name": "python"}, {"name_field": "name"})
        assert score > 0.9


class TestTemporalSim:
    def test_both_none(self):
        m = PairwiseMatcher.__new__(PairwiseMatcher)
        assert m._temporal_sim({}, {}) == 0.5

    def test_overlap(self):
        m = PairwiseMatcher.__new__(PairwiseMatcher)
        a = {"start_date": date(2020, 1, 1), "end_date": date(2021, 1, 1)}
        b = {"start_date": date(2020, 6, 1), "end_date": date(2021, 6, 1)}
        assert m._temporal_sim(a, b) == 1.0

    def test_no_overlap(self):
        m = PairwiseMatcher.__new__(PairwiseMatcher)
        a = {"start_date": date(2020, 1, 1), "end_date": date(2020, 6, 1)}
        b = {"start_date": date(2021, 1, 1), "end_date": date(2021, 6, 1)}
        assert m._temporal_sim(a, b) == 0.0

    def test_one_sided(self):
        m = PairwiseMatcher.__new__(PairwiseMatcher)
        a = {"start_date": date(2020, 1, 1), "end_date": date(2021, 1, 1)}
        b = {"start_date": None, "end_date": None}
        assert m._temporal_sim(a, b) == 0.5

    def test_issued_on_fallback(self):
        m = PairwiseMatcher.__new__(PairwiseMatcher)
        a = {"issued_on": date(2020, 1, 1), "expires_on": date(2021, 1, 1)}
        b = {"issued_on": date(2020, 6, 1), "expires_on": date(2021, 6, 1)}
        assert m._temporal_sim(a, b) == 1.0
