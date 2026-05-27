"""Unit tests for mock job parser (pure, no DB)."""
from __future__ import annotations

import pytest

from src.documents.infrastructure.job_parser import MockJobParser, _guess_language


class TestMockJobParser:
    @pytest.fixture
    def parser(self):
        return MockJobParser()

    async def test_empty_returns_minimal(self, parser):
        result = await parser.parse(url=None, description=None)
        assert result["title"] is None
        assert result["company"] is None
        assert result["description_raw"] == ""
        assert result["hard_skills"] == []

    async def test_url_only(self, parser):
        result = await parser.parse(url="https://example.com/job", description=None)
        assert "example.com" in result["description_raw"]

    async def test_ats_detection(self, parser):
        result = await parser.parse(
            url=None, description="We use greenhouse for recruiting"
        )
        assert result["ats"] == "Greenhouse"

    async def test_hard_skills(self, parser):
        result = await parser.parse(
            url=None, description="Looking for Python, React and PostgreSQL"
        )
        assert "Python" in result["hard_skills"]
        assert "React" in result["hard_skills"]
        assert "PostgreSQL" in result["hard_skills"]

    async def test_soft_skills(self, parser):
        result = await parser.parse(
            url=None, description="Communication and leadership are key"
        )
        assert "communication" in result["soft_skills"]
        assert "leadership" in result["soft_skills"]

    async def test_title_extraction(self, parser):
        result = await parser.parse(
            url=None, description="We need a senior developer"
        )
        assert result["title"] == "Senior Developer"

    async def test_company_extraction(self, parser):
        result = await parser.parse(
            url=None, description="Join us at AcmeCorp"
        )
        assert result["company"] == "AcmeCorp"

    async def test_must_haves_nice_to_haves(self, parser):
        result = await parser.parse(
            url=None, description="Python TypeScript React Django Flask Go Rust"
        )
        assert len(result["must_haves"]) == 5
        assert len(result["nice_to_haves"]) == 2

    async def test_language_detection_spanish(self, parser):
        result = await parser.parse(
            url=None, description="Buscamos una persona para experiencia con conocimientos"
        )
        assert result["language"] == "es"

    async def test_language_detection_english(self, parser):
        result = await parser.parse(
            url=None, description="Looking for a great candidate"
        )
        assert result["language"] == "en"


class TestGuessLanguage:
    def test_empty(self):
        assert _guess_language("") == "es"

    def test_spanish(self):
        assert _guess_language("experiencia y conocimientos imprescindible") == "es"

    def test_english(self):
        assert _guess_language("looking for experience") == "en"
