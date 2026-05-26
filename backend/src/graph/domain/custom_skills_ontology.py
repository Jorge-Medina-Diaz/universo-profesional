"""Extended ontology for AI-era skills not present in ESCO.

ESCO (European Skills/Competences framework) covers traditional occupations
and competencies well, but lags behind the fast-moving AI/LLM engineering
landscape. This module provides a curated, embeddable fallback ontology so
that skills like "MCP", "RAG pipeline", or "CrewAI" can still be linked to
a canonical concept when the ESCO linker returns ORPHAN.

Each entry carries:
  • uri          — stable URI within our own namespace
  • pref_label   — primary human-readable label (es/en)
  • description  — short definition for embedding text
  • related_uris — optional cross-links for graph traversal

The ontology is loaded in-memory (small — <100 concepts) and indexed via
pgvector alongside ESCO when needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CustomSkillConcept:
    uri: str
    pref_label_es: str
    pref_label_en: str
    description: str
    related_uris: tuple[str, ...] = ()

    @property
    def embedding_text(self) -> str:
        """Text used to compute the embedding vector."""
        return f"{self.pref_label_en}. {self.pref_label_es}. {self.description}"


# ---------------------------------------------------------------------------
# AI / LLM Engineering skills
# ---------------------------------------------------------------------------

_CUSTOM_SKILLS: list[CustomSkillConcept] = [
    CustomSkillConcept(
        uri="up:ai/mcp",
        pref_label_es="Model Context Protocol",
        pref_label_en="Model Context Protocol",
        description="Protocolo abierto para integrar fuentes de contexto externas con LLMs mediante servidores MCP.",
    ),
    CustomSkillConcept(
        uri="up:ai/agent-orchestration",
        pref_label_es="Orquestación de agentes de IA",
        pref_label_en="Agent Orchestration",
        description="Diseño y coordinación de flujos multi-agente con herramientas, memoria y planificación autónoma.",
    ),
    CustomSkillConcept(
        uri="up:ai/prompt-engineering",
        pref_label_es="Prompt Engineering",
        pref_label_en="Prompt Engineering",
        description="Diseño, optimización y evaluación de prompts para modelos de lenguaje grandes (LLMs).",
    ),
    CustomSkillConcept(
        uri="up:ai/vector-databases",
        pref_label_es="Bases de datos vectoriales",
        pref_label_en="Vector Databases",
        description="Administración y consulta de bases de datos vectoriales (pgvector, Pinecone, Weaviate, Milvus) para RAG.",
    ),
    CustomSkillConcept(
        uri="up:ai/rag-pipeline",
        pref_label_es="RAG pipeline",
        pref_label_en="RAG Pipeline",
        description="Construcción de pipelines Retrieval-Augmented Generation: chunking, embedding, recuperación híbrida y reranking.",
    ),
    CustomSkillConcept(
        uri="up:ai/llm-fine-tuning",
        pref_label_es="Fine-tuning de LLM",
        pref_label_en="LLM Fine-Tuning",
        description="Ajuste fino de modelos de lenguaje grandes con técnicas LoRA, QLoRA, RLHF y DPO.",
    ),
    CustomSkillConcept(
        uri="up:ai/rlhf",
        pref_label_es="Reinforcement Learning from Human Feedback",
        pref_label_en="RLHF",
        description="Alineación de modelos generativos mediante aprendizaje por refuerzo con retroalimentación humana.",
    ),
    CustomSkillConcept(
        uri="up:ai/langchain",
        pref_label_es="LangChain",
        pref_label_en="LangChain",
        description="Framework en Python/JS para construir aplicaciones con LLMs mediante cadenas, agentes y herramientas.",
    ),
    CustomSkillConcept(
        uri="up:ai/llamaindex",
        pref_label_es="LlamaIndex",
        pref_label_en="LlamaIndex",
        description="Framework para indexar, consultar y orquestar datos privados con LLMs y RAG.",
    ),
    CustomSkillConcept(
        uri="up:ai/crewai",
        pref_label_es="CrewAI",
        pref_label_en="CrewAI",
        description="Framework multi-agente basado en roles para equipos autónomos de IA que colaboran en tareas complejas.",
    ),
]


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

_BY_URI: dict[str, CustomSkillConcept] = {c.uri: c for c in _CUSTOM_SKILLS}
_BY_LABEL_NORM: dict[str, CustomSkillConcept] = {}


def _norm(label: str) -> str:
    return " ".join(label.lower().strip().split())


def _build_index() -> None:
    global _BY_LABEL_NORM
    if _BY_LABEL_NORM:
        return
    for c in _CUSTOM_SKILLS:
        for label in (c.pref_label_es, c.pref_label_en):
            _BY_LABEL_NORM[_norm(label)] = c
            # Also index without parentheses / acronyms split
            simple = label.split("(")[0].strip()
            if simple != label:
                _BY_LABEL_NORM[_norm(simple)] = c


_build_index()


def find_by_uri(uri: str) -> CustomSkillConcept | None:
    return _BY_URI.get(uri)


def find_by_label(label: str) -> CustomSkillConcept | None:
    return _BY_LABEL_NORM.get(_norm(label))


def search_by_text(query: str) -> list[CustomSkillConcept]:
    """Very cheap keyword search over the small ontology."""
    tokens = set(_norm(query).split())
    scored: list[tuple[int, CustomSkillConcept]] = []
    for c in _CUSTOM_SKILLS:
        text = _norm(c.embedding_text)
        score = sum(1 for t in tokens if t in text)
        if score:
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]


def all_concepts() -> list[CustomSkillConcept]:
    return list(_CUSTOM_SKILLS)


def to_embedding_rows() -> list[dict[str, Any]]:
    """Rows ready for bulk insert into `ontology_embeddings`-style table."""
    return [
        {
            "uri": c.uri,
            "label": "CustomSkill",
            "pref_label_es": c.pref_label_es,
            "pref_label_en": c.pref_label_en,
            "embedding_text": c.embedding_text,
        }
        for c in _CUSTOM_SKILLS
    ]
