"""Unit tests for the pure match-scoring helper (no DB, no embeddings)."""
from __future__ import annotations

from src.documents.application.match_scoring import compute_match_breakdown


def _row(entity_type: str, score: float) -> dict:
    return {"entity_type": entity_type, "entity_id": "x", "score": score, "fields": {}}


class TestComputeMatchBreakdown:
    def test_empty_retrieval_scores_zero(self):
        out = compute_match_breakdown(retrieved=[], needed_keywords=[], your_skills=[])
        assert out["match_score"] == 0
        assert out["dimensions"] == {"skills": None, "experience": None, "education": None}
        assert out["gaps"] == []
        assert out["strengths"] == []
        assert out["keyword_coverage"] is None

    def test_buckets_entities_into_dimensions(self):
        out = compute_match_breakdown(
            retrieved=[
                _row("skill", 0.9),
                _row("certification", 0.8),  # also a "skills" dimension contributor
                _row("experience", 0.6),
                _row("project", 0.4),  # "experience" dimension
                _row("education", 0.2),
            ],
            needed_keywords=[],
            your_skills=[],
        )
        assert out["dimensions"]["skills"] is not None
        assert out["dimensions"]["experience"] is not None
        assert out["dimensions"]["education"] is not None
        # Skills bucket (0.9, 0.8) should outscore experience (0.6, 0.4)
        assert out["dimensions"]["skills"] > out["dimensions"]["experience"]
        # Education bucket only has the weak 0.2 row → lowest
        assert out["dimensions"]["education"] < out["dimensions"]["experience"]

    def test_education_none_when_no_education_entities(self):
        out = compute_match_breakdown(
            retrieved=[_row("skill", 0.9)], needed_keywords=[], your_skills=[]
        )
        assert out["dimensions"]["education"] is None
        assert out["dimensions"]["skills"] is not None

    def test_gaps_strengths_keyword_coverage(self):
        out = compute_match_breakdown(
            retrieved=[_row("skill", 0.8)],
            needed_keywords=["Python", "Kubernetes", "AWS"],
            your_skills=["python", "Docker", "AWS"],
        )
        # Case-insensitive set intersection / difference
        assert out["strengths"] == ["aws", "python"]
        assert out["gaps"] == ["kubernetes"]
        # 2 of 3 needed keywords covered
        assert out["keyword_coverage"] == 67

    def test_headline_score_matches_legacy_formula(self):
        # Legacy: round(clamp((mean(score)+1)/2) * 100)
        out = compute_match_breakdown(
            retrieved=[_row("skill", 1.0), _row("experience", 0.0)],
            needed_keywords=[],
            your_skills=[],
        )
        # mean = 0.5 → (0.5+1)/2 = 0.75 → 75
        assert out["match_score"] == 75

    def test_suggested_keywords_capped_at_15(self):
        out = compute_match_breakdown(
            retrieved=[],
            needed_keywords=[f"kw{i}" for i in range(20)],
            your_skills=[],
        )
        assert len(out["suggested_keywords"]) == 15
