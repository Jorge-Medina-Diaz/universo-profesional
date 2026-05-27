"""Unit tests for cross_encoder pure helpers."""
from __future__ import annotations

from src.graph.application.cross_encoder import (
    FeatureReranker,
    _exact_substring_bonus,
    _jaccard,
    _jaro_winkler,
    _tokenize,
)
from src.graph.domain.esco_types import EscoCandidate


class TestTokenize:
    def test_basic(self):
        assert _tokenize("Hello World") == {"hello", "world"}


class TestJaccard:
    def test_identical(self):
        assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0

    def test_no_overlap(self):
        assert _jaccard({"a"}, {"b"}) == 0.0

    def test_empty(self):
        assert _jaccard(set(), {"a"}) == 0.0


class TestExactSubstringBonus:
    def test_exact_match(self):
        assert _exact_substring_bonus("Python", "Python") == 1.0

    def test_substring(self):
        assert _exact_substring_bonus("Python", "Python 3") == 0.5

    def test_no_match(self):
        assert _exact_substring_bonus("Java", "Python") == 0.0


class TestJaroWinkler:
    def test_identical(self):
        assert _jaro_winkler("python", "python") == 1.0

    def test_different(self):
        assert _jaro_winkler("python", "java") < 1.0


class TestFeatureReranker:
    def test_rerank_empty(self):
        r = FeatureReranker()
        assert r.rerank("python", []) == []

    def test_rerank_returns_scores(self):
        r = FeatureReranker()
        cands = [
            EscoCandidate(uri="http://x/1", label="Python", pref_label_en="Python"),
            EscoCandidate(uri="http://x/2", label="Java", pref_label_en="Java"),
        ]
        scores = r.rerank("python", cands)
        assert len(scores) == 2
        assert scores[0].rerank_score >= scores[1].rerank_score

    def test_best_below_threshold(self):
        r = FeatureReranker()
        cands = [EscoCandidate(uri="http://x/1", label="XYZ", pref_label_en="XYZ")]
        assert r.best("abc", cands, threshold=0.99) is None

    def test_best_above_threshold(self):
        r = FeatureReranker()
        cands = [EscoCandidate(uri="http://x/1", label="Python", pref_label_en="Python")]
        best = r.best("python", cands, threshold=0.1)
        assert best is not None
