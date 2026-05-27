"""Unit tests for UniverseEnrichmentEngine."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.agents.workflows.universe_enrichment import (
    EnrichmentResult,
    ExtractedEntity,
    ExtractedRelation,
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
        with patch.object(engine, "_call_llm", return_value=raw):
            entities = await engine._extract_entities("I know Python and work at ACME")
        assert len(entities) == 2
        assert entities[0].kind == "skill"
        assert entities[0].payload["name"] == "Python"

    async def test_parses_json_inside_markdown_fence(self, engine):
        raw = '```json\n[{"kind": "skill", "payload": {"name": "Rust"}}]\n```'
        with patch.object(engine, "_call_llm", return_value=raw):
            entities = await engine._extract_entities("I love Rust")
        assert len(entities) == 1
        assert entities[0].kind == "skill"

    async def test_empty_input_returns_empty(self, engine):
        entities = await engine._extract_entities("")
        assert entities == []

    async def test_malformed_response_returns_empty(self, engine):
        with patch.object(engine, "_call_llm", return_value="not json"):
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
        with patch.object(engine, "_call_llm", return_value=raw):
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

    async def test_process_creates_entities_and_relations(self, engine):
        ent_raw = json.dumps(
            [
                {"kind": "skill", "payload": {"name": "Python"}},
                {"kind": "experience", "payload": {"organization": "ACME"}},
            ]
        )
        rel_raw = json.dumps(
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

        with patch.object(engine, "_call_llm", side_effect=[ent_raw, rel_raw]):
            with patch.object(engine, "_upsert_entity", return_value=uuid4()):
                with patch.object(engine, "_link_to_esco", return_value=False):
                    with patch(
                        "src.agents.workflows.universe_enrichment.universe_graph_service.upsert_edge",
                        new_callable=AsyncMock,
                    ) as mock_edge:
                        with patch(
                            "src.universe.application.enrichment.enrich_user_graph",
                            new_callable=AsyncMock,
                        ):
                            result = await engine.process("I use Python at ACME")

        assert result.entities_created == 2
        assert result.relations_created == 1
        mock_edge.assert_awaited_once()
