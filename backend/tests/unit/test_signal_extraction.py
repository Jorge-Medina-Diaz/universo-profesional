"""Unit tests for signal_extraction pure helpers."""
from __future__ import annotations

from src.universe.application.signal_extraction import (
    _classify_status,
    _cosine,
    _keyword_overlap,
    _vec_literal,
)


class TestKeywordOverlap:
    def test_true_when_two_shared_words(self):
        assert _keyword_overlap("python fastapi django", "python flask django") is True

    def test_false_when_less_than_two(self):
        assert _keyword_overlap("python fastapi", "flask django") is False

    def test_ignores_short_words(self):
        assert _keyword_overlap("a b c d", "a b c d") is False


class TestCosine:
    def test_empty_returns_zero(self):
        assert _cosine([], [1, 2]) == 0.0
        assert _cosine([1, 2], []) == 0.0

    def test_identical_vectors(self):
        assert _cosine([1, 0], [1, 0]) == 1.0

    def test_orthogonal_vectors(self):
        assert _cosine([1, 0], [0, 1]) == 0.0


class TestClassifyStatus:
    def test_anti_pattern(self):
        assert _classify_status("anti_patterns", 0.8) == "avoid"
        assert _classify_status("anti_patterns", 0.5) is None

    def test_own(self):
        assert _classify_status("signals", 0.8) == "own"

    def test_practice(self):
        assert _classify_status("signals", 0.7) == "practice"

    def test_aspire(self):
        assert _classify_status("signals", 0.6) == "aspire"

    def test_none(self):
        assert _classify_status("signals", 0.5) is None


class TestVecLiteral:
    def test_format(self):
        assert _vec_literal([1.0, 2.0]) == "[1.0000000,2.0000000]"
