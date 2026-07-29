"""Unit tests for UniverseEnrichmentEngine pure helpers (no DB)."""
from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from src.agents.workflows.universe_enrichment import (
    EnrichmentResult,
    ExtractedEntity,
    ExtractedRelation,
    UniverseEnrichmentEngine,
)


class TestCanonicalName:
    def test_skill(self):
        engine = UniverseEnrichmentEngine(MagicMock(), uuid4())
        ent = ExtractedEntity(kind="skill", payload={"name": "  Python  "})
        assert engine._canonical_name(ent) == "python"

    def test_experience(self):
        engine = UniverseEnrichmentEngine(MagicMock(), uuid4())
        ent = ExtractedEntity(kind="experience", payload={"organization": "Google"})
        assert engine._canonical_name(ent) == "google"

    def test_course(self):
        engine = UniverseEnrichmentEngine(MagicMock(), uuid4())
        ent = ExtractedEntity(kind="course", payload={"title": "RAG 101"})
        assert engine._canonical_name(ent) == "rag 101"

    def test_fallback(self):
        engine = UniverseEnrichmentEngine(MagicMock(), uuid4())
        ent = ExtractedEntity(kind="unknown", payload={"name": "X", "title": "Y"})
        assert engine._canonical_name(ent) == "x"

    def test_empty(self):
        engine = UniverseEnrichmentEngine(MagicMock(), uuid4())
        ent = ExtractedEntity(kind="skill", payload={})
        assert engine._canonical_name(ent) == ""


class TestEnrichmentResult:
    def test_defaults(self):
        r = EnrichmentResult()
        assert r.entities_created == 0
        assert r.errors == []


class TestExtractedRelation:
    def test_defaults(self):
        r = ExtractedRelation(
            source_kind="experience",
            source_name="google",
            edge_type="USES_TECH",
            target_kind="skill",
            target_name="python",
        )
        assert r.properties == {}
