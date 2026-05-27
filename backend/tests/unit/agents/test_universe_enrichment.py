"""Unit tests for UniverseEnrichmentEngine."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.agents.workflows.universe_enrichment import (
    ExtractedEntity,
    UniverseEnrichmentEngine,
)


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def engine(mock_session):
    user_id = uuid4()
    return UniverseEnrichmentEngine(mock_session, user_id)


class TestExtractEntities:
    async def test_parses_valid_json_array(self, engine):
        raw = json.dumps(
            [
                {"kind": "skill", "payload": {"name": "Python", "level": "expert"}},
                {"kind": "experience", "payload": {"organization": "ACME", "role": "Dev"}},
            ]
        )
        engine._call_llm = AsyncMock(return_value=raw)
        entities = await engine._extract_entities("I know Python and work at ACME")
        assert len(entities) == 2
        assert entities[0].kind == "skill"
        assert entities[0].payload["name"] == "Python"

    async def test_parses_json_inside_markdown_fence(self, engine):
        raw = '```json\n[{"kind": "skill", "payload": {"name": "Rust"}}]\n```'
        engine._call_llm = AsyncMock(return_value=raw)
        entities = await engine._extract_entities("I love Rust")
        assert len(entities) == 1
        assert entities[0].kind == "skill"

    async def test_empty_input_returns_empty(self, engine):
        entities = await engine._extract_entities("")
        assert entities == []

    async def test_malformed_response_returns_empty(self, engine):
        engine._call_llm = AsyncMock(return_value="not json")
        entities = await engine._extract_entities("blah")
        assert entities == []


class TestExtractRelations:
    async def test_parses_valid_relations(self, engine):
        raw = json.dumps(
            [
                {
                    "source_kind": "experience",
                    "source_name": "acme",
                    "edge_type": "USES_TECH",
                    "target_kind": "skill",
                    "target_name": "python",
                }
            ]
        )
        entities = [
            ExtractedEntity(kind="experience", payload={"organization": "ACME"}),
            ExtractedEntity(kind="skill", payload={"name": "Python"}),
        ]
        engine._call_llm = AsyncMock(return_value=raw)
        relations = await engine._extract_relations("I used Python at ACME", entities)
        assert len(relations) == 1
        assert relations[0].edge_type == "USES_TECH"


class TestCanonicalName:
    def test_skill_uses_name(self, engine):
        ent = ExtractedEntity(kind="skill", payload={"name": "Docker"})
        assert engine._canonical_name(ent) == "docker"

    def test_experience_uses_organization(self, engine):
        ent = ExtractedEntity(kind="experience", payload={"organization": "  Google  "})
        assert engine._canonical_name(ent) == "google"

    def test_project_uses_name(self, engine):
        ent = ExtractedEntity(kind="project", payload={"name": "Alpha"})
        assert engine._canonical_name(ent) == "alpha"

    def test_course_uses_title(self, engine):
        ent = ExtractedEntity(kind="course", payload={"title": "ML 101"})
        assert engine._canonical_name(ent) == "ml 101"


class TestProcess:
    async def test_empty_text_returns_zero_counts(self, engine):
        result = await engine.process("")
        assert result.entities_created == 0
        assert result.relations_created == 0
        assert result.errors == []
