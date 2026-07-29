"""Unit tests for area_keywords — pure text processing."""
from __future__ import annotations

from src.universe.application.area_keywords import (
    area_hits_per_kw,
    collect_text_blob,
    primary_area,
    score_areas,
)


class TestCollectTextBlob:
    def test_joins_and_lowercases(self):
        assert collect_text_blob(["Hello", None, "World"]) == "hello world"

    def test_empty(self):
        assert collect_text_blob([]) == ""
        assert collect_text_blob([None, ""]) == ""


class TestScoreAreas:
    def test_backend_hits(self):
        blob = "python fastapi postgresql"
        scores = score_areas(blob)
        assert "backend" in scores
        assert scores["backend"] >= 3

    def test_frontend_hits(self):
        blob = "react typescript css"
        scores = score_areas(blob)
        assert "frontend" in scores

    def test_empty(self):
        assert score_areas("") == {}

    def test_multiple_areas(self):
        blob = "python react kubernetes aws"
        scores = score_areas(blob)
        assert "backend" in scores
        assert "frontend" in scores
        assert "devops" in scores
        assert "cloud" in scores


class TestAreaHitsPerKw:
    def test_counts_hits(self):
        assert area_hits_per_kw("python django", "backend") >= 2

    def test_unknown_area(self):
        assert area_hits_per_kw("python", "unknown_area") == 0


class TestPrimaryArea:
    def test_returns_best(self):
        assert primary_area("python django fastapi") == "backend"
        assert primary_area("react typescript") == "frontend"

    def test_none_when_no_match(self):
        assert primary_area("cooking gardening") is None
