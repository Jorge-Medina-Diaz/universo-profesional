"""Unit tests for the FeatureReranker (CrossEncoder)."""
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
    def test_splits_on_whitespace(self):
        assert _tokenize("Hello World") == {"hello", "world"}

    def test_lowercases(self):
        assert _tokenize("Python") == {"python"}

    def test_empty_string(self):
        assert _tokenize("") == set()

    def test_multiple_spaces(self):
        assert _tokenize("a  b   c") == {"a", "b", "c"}


class TestJaccard:
    def test_identical_sets(self):
        assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0

    def test_no_overlap(self):
        assert _jaccard({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        assert _jaccard({"a", "b", "c"}, {"b", "c", "d"}) == 0.5

    def test_empty_a(self):
        assert _jaccard(set(), {"a"}) == 0.0

    def test_empty_b(self):
        assert _jaccard({"a"}, set()) == 0.0

    def test_both_empty(self):
        assert _jaccard(set(), set()) == 0.0


class TestJaroWinkler:
    def test_exact_match(self):
        assert _jaro_winkler("python", "python") == 1.0

    def test_completely_different(self):
        assert _jaro_winkler("abc", "xyz") < 0.3

    def test_typo_tolerance(self):
        score = _jaro_winkler("python", "pythn")
        assert score > 0.9

    def test_prefix_boost(self):
        score = _jaro_winkler("javascript", "java")
        assert score > 0.7

    def test_empty_string(self):
        assert _jaro_winkler("", "something") == 0.0

    def test_non_ascii(self):
        score = _jaro_winkler("python", "pythön")
        assert score > 0.8


class TestExactSubstringBonus:
    def test_exact_match(self):
        assert _exact_substring_bonus("python", "python") == 1.0

    def test_query_in_candidate(self):
        assert _exact_substring_bonus("python", "python programming") == 0.5

    def test_candidate_in_query(self):
        assert _exact_substring_bonus("python programming", "python") == 0.5

    def test_no_substring(self):
        assert _exact_substring_bonus("python", "java") == 0.0

    def test_case_insensitive(self):
        assert _exact_substring_bonus("Python", "PYTHON") == 1.0


class TestRankDecay:
    def test_rank_zero_is_one(self):
        reranker = FeatureReranker()
        candidates = [
            EscoCandidate(uri="http://example.com/1", label="Skill", pref_label_es="python", score=0.8),
        ]
        result = reranker.rerank("python", candidates)
        assert result[0].features["rank_decay"] == 1.0

    def test_rank_one_is_point_nine_five(self):
        reranker = FeatureReranker()
        candidates = [
            EscoCandidate(uri="http://example.com/1", label="Skill", pref_label_es="python", score=0.8),
            EscoCandidate(uri="http://example.com/2", label="Skill", pref_label_es="java", score=0.7),
        ]
        result = reranker.rerank("python", candidates)
        # Find the java candidate (should be rank 1 originally)
        java_entry = next(r for r in result if r.candidate.uri.endswith("/2"))
        assert java_entry.features["rank_decay"] == 0.95

    def test_rank_ten_floor(self):
        reranker = FeatureReranker()
        candidates = [
            EscoCandidate(uri=f"http://example.com/{i}", label="Skill", pref_label_es=f"skill{i}", score=0.5)
            for i in range(15)
        ]
        result = reranker.rerank("python", candidates)
        # Rank 10 should be max(0.5, 1.0 - 10*0.05) = 0.5
        rank_ten = next(r for r in result if r.features["rank_decay"] == 0.5)
        assert rank_ten is not None


class TestOverallRerankOrdering:
    def test_exact_match_wins(self):
        reranker = FeatureReranker()
        candidates = [
            EscoCandidate(uri="http://example.com/1", label="Skill", pref_label_es="java programming", score=0.85),
            EscoCandidate(uri="http://example.com/2", label="Skill", pref_label_es="python", score=0.80),
        ]
        result = reranker.rerank("python", candidates)
        assert result[0].candidate.uri.endswith("/2")
        assert result[0].rerank_score > result[1].rerank_score

    def test_rerank_preserves_length(self):
        reranker = FeatureReranker()
        candidates = [
            EscoCandidate(uri="http://example.com/1", label="Skill", pref_label_es="python", score=0.8),
            EscoCandidate(uri="http://example.com/2", label="Skill", pref_label_es="java", score=0.7),
            EscoCandidate(uri="http://example.com/3", label="Skill", pref_label_es="rust", score=0.6),
        ]
        result = reranker.rerank("python", candidates)
        assert len(result) == 3

    def test_descending_order(self):
        reranker = FeatureReranker()
        candidates = [
            EscoCandidate(uri="http://example.com/1", label="Skill", pref_label_es="python", score=0.6),
            EscoCandidate(uri="http://example.com/2", label="Skill", pref_label_es="python data", score=0.5),
            EscoCandidate(uri="http://example.com/3", label="Skill", pref_label_es="java", score=0.9),
        ]
        result = reranker.rerank("python", candidates)
        scores = [r.rerank_score for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_features_populated(self):
        reranker = FeatureReranker()
        candidates = [
            EscoCandidate(uri="http://example.com/1", label="Skill", pref_label_es="python", score=0.8),
        ]
        result = reranker.rerank("python", candidates)
        assert "jaro_winkler" in result[0].features
        assert "jaccard" in result[0].features
        assert "exact_bonus" in result[0].features
        assert "rank_decay" in result[0].features

    def test_fallback_label_from_uri(self):
        """When pref_label is missing, the reranker extracts a label from the URI."""
        reranker = FeatureReranker()
        candidates = [
            EscoCandidate(uri="http://data.europa.eu/esco/skill/python-programming", label="Skill", pref_label_es=None, pref_label_en=None, score=0.8),
        ]
        result = reranker.rerank("python", candidates)
        # Should not crash and should produce some score
        assert result[0].rerank_score > 0

    def test_best_returns_top_above_threshold(self):
        reranker = FeatureReranker()
        candidates = [
            EscoCandidate(uri="http://example.com/1", label="Skill", pref_label_es="python", score=0.8),
        ]
        best = reranker.best("python", candidates, threshold=0.5)
        assert best is not None
        assert best.uri.endswith("/1")

    def test_best_returns_none_below_threshold(self):
        reranker = FeatureReranker()
        candidates = [
            EscoCandidate(uri="http://example.com/1", label="Skill", pref_label_es="java", score=0.8),
        ]
        best = reranker.best("python", candidates, threshold=0.99)
        assert best is None

    def test_best_mutates_candidate_score(self):
        reranker = FeatureReranker()
        candidates = [
            EscoCandidate(uri="http://example.com/1", label="Skill", pref_label_es="python", score=0.8),
        ]
        best = reranker.best("python", candidates, threshold=0.5)
        assert best is not None
        assert best.score == candidates[0].score  # mutated in-place

    def test_custom_weights(self):
        reranker = FeatureReranker()
        candidates = [
            EscoCandidate(uri="http://example.com/1", label="Skill", pref_label_es="python", score=0.8),
        ]
        custom_weights = {"jaro_winkler": 0.0, "jaccard": 0.0, "exact_bonus": 1.0, "rank_decay": 0.0}
        result = reranker.rerank("python", candidates, weights=custom_weights)
        # exact_bonus for exact match is 1.0, so rerank_score should be 1.0
        assert result[0].rerank_score == 1.0

    def test_empty_candidates(self):
        reranker = FeatureReranker()
        result = reranker.rerank("python", [])
        assert result == []

    def test_best_empty_candidates(self):
        reranker = FeatureReranker()
        best = reranker.best("python", [], threshold=0.5)
        assert best is None
