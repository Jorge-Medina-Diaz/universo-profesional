"""Unit tests for custom skills ontology (pure, no DB)."""
from __future__ import annotations

from src.graph.domain.custom_skills_ontology import (
    CustomSkillConcept,
    all_concepts,
    find_by_label,
    find_by_uri,
    search_by_text,
    to_embedding_rows,
)


class TestCustomSkillConcept:
    def test_embedding_text(self):
        c = CustomSkillConcept(
            uri="up:test",
            pref_label_es="Prueba",
            pref_label_en="Test",
            description="A test concept.",
        )
        assert c.embedding_text == "Test. Prueba. A test concept."


class TestFindByUri:
    def test_known(self):
        c = find_by_uri("up:ai/mcp")
        assert c is not None
        assert c.pref_label_en == "Model Context Protocol"

    def test_unknown(self):
        assert find_by_uri("up:ai/unknown") is None


class TestFindByLabel:
    def test_exact(self):
        c = find_by_label("LangChain")
        assert c is not None
        assert c.uri == "up:ai/langchain"

    def test_case_insensitive(self):
        c = find_by_label("langchain")
        assert c is not None

    def test_unknown(self):
        assert find_by_label("foobar") is None


class TestSearchByText:
    def test_keyword_hit(self):
        hits = search_by_text("vector database")
        assert len(hits) > 0
        assert any("vector" in h.embedding_text.lower() for h in hits)

    def test_no_match(self):
        hits = search_by_text("xyz123nonsense")
        assert hits == []

    def test_scored_ordering(self):
        hits = search_by_text("agent orchestration")
        # "agent" and "orchestration" both appear in the agent-orchestration concept
        assert hits[0].uri == "up:ai/agent-orchestration"


class TestAllConcepts:
    def test_non_empty(self):
        concepts = all_concepts()
        assert len(concepts) > 0
        assert all(isinstance(c, CustomSkillConcept) for c in concepts)


class TestToEmbeddingRows:
    def test_structure(self):
        rows = to_embedding_rows()
        assert len(rows) > 0
        assert all(
            set(r.keys()) == {"uri", "label", "pref_label_es", "pref_label_en", "embedding_text"}
            for r in rows
        )
