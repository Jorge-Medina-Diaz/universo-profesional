"""Unit tests for document LLM client pure helpers (no DB)."""
from __future__ import annotations

from src.documents.infrastructure.llm_client import (
    _empty_cover_letter,
    _empty_resume,
    _facts_for_prompt,
    _job_for_prompt,
)


class TestFactsForPrompt:
    def test_empty_resume(self):
        text = _facts_for_prompt({})
        assert "name" in text
        assert "skills" in text

    def test_with_data(self):
        resume = {
            "basics": {"name": "Alice", "label": "Dev", "summary": "Summary"},
            "skills": [{"name": "Python"}],
            "languages": [{"language": "English", "fluency": "C2"}],
            "work": [
                {
                    "name": "Acme",
                    "position": "Dev",
                    "summary": "Built stuff",
                    "highlights": ["Led team"],
                }
            ],
            "projects": [{"name": "P1", "description": "Desc", "keywords": ["Py"]}],
            "education": [
                {"institution": "MIT", "studyType": "BSc", "area": "CS"}
            ],
        }
        text = _facts_for_prompt(resume)
        assert "Alice" in text
        assert "Python" in text
        assert "Acme" in text


class TestJobForPrompt:
    def test_empty(self):
        text = _job_for_prompt({})
        assert "title" in text

    def test_with_data(self):
        job = {
            "title": "Senior Dev",
            "company": "Acme",
            "must_haves": ["Python"],
            "ats_keywords": ["Python", "React"],
            "description_raw": "We need a great dev",
        }
        text = _job_for_prompt(job)
        assert "Senior Dev" in text
        assert "Acme" in text
        assert "Python" in text


class TestEmptyResume:
    def test_structure(self):
        r = _empty_resume("en")
        assert r["work"] == []
        assert r["skills"] == []
        assert r["meta"]["language"] == "en"


class TestEmptyCoverLetter:
    def test_structure(self):
        c = _empty_cover_letter("es")
        assert c["cover_letter_body"] == ""
        assert c["meta"]["language"] == "es"
        assert c["meta"]["kind"] == "cover_letter"
