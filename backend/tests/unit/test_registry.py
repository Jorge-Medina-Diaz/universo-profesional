"""Unit tests for graph domain registry."""
from __future__ import annotations

from src.graph.domain.registry import (
    _achievement_text,
    _adr_text,
    _artifact_text,
    _cert_text,
    _course_text,
    _education_text,
    _experience_text,
    _interest_text,
    _is_blank,
    _language_text,
    _project_text,
    _skill_text,
    completeness,
    core_fields,
    kinds_with_evidence,
    kinds_with_ontology,
    missing_core_fields,
)


class TestTextBuilders:
    def test_skill_text(self):
        assert _skill_text({"name": "Python", "category": "hard", "level": "expert"}) == "Python hard expert"

    def test_experience_text(self):
        assert "Engineer" in _experience_text({"role": "Engineer", "organization": "Acme"})

    def test_education_text(self):
        assert "USE" in _education_text({"institution": "USE", "degree": "BSc"})

    def test_project_text(self):
        assert "demo" in _project_text({"name": "demo", "tech_stack": ["python"]})

    def test_cert_text(self):
        assert "AWS" in _cert_text({"name": "AWS", "issuer": "Amazon"})

    def test_course_text(self):
        assert "RAG" in _course_text({"title": "RAG", "platform": "DLAI"})

    def test_language_text(self):
        assert "en" in _language_text({"code": "en", "name": "English", "level": "C1"})

    def test_achievement_text(self):
        assert "Best" in _achievement_text({"title": "Best", "description": "Paper"})

    def test_interest_text(self):
        assert "RAG" in _interest_text({"name": "RAG"})

    def test_artifact_text(self):
        assert "talk" in _artifact_text({"type": "talk", "title": "T"})

    def test_adr_text(self):
        assert "ADR-1" in _adr_text({"title": "ADR-1", "context": "x"})


class TestKindsQueries:
    def test_kinds_with_ontology(self):
        assert "skill" in kinds_with_ontology()

    def test_kinds_with_evidence(self):
        assert "skill" in kinds_with_evidence()


class TestCoreFields:
    def test_known_kind(self):
        assert "name" in core_fields("skill")

    def test_unknown_kind(self):
        assert core_fields("unknown") == ()


class TestIsBlank:
    def test_none(self):
        assert _is_blank(None) is True

    def test_empty_string(self):
        assert _is_blank("  ") is True

    def test_empty_list(self):
        assert _is_blank([]) is True

    def test_zero(self):
        assert _is_blank(0) is False


class TestMissingCoreFields:
    def test_missing(self):
        assert "name" in missing_core_fields("skill", {})

    def test_present(self):
        assert missing_core_fields("skill", {"name": "Python", "level": "expert", "years": 5}) == []


class TestCompleteness:
    def test_complete(self):
        assert completeness("interest", {"name": "RAG"}) == 1.0

    def test_partial(self):
        assert completeness("skill", {"name": "Python"}) == 0.33

    def test_unknown_kind(self):
        assert completeness("unknown", {}) == 1.0
