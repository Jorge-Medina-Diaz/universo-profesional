"""Smoke tests for the consolidated GRAPH_REGISTRY (pure, no DB).

GRAPH_REGISTRY is the single source of truth after the registry
consolidation. These tests guard against an entry going half-defined.
"""
from __future__ import annotations

from src.graph.domain.registry import (
    GRAPH_REGISTRY,
    kinds_with_evidence,
    kinds_with_ontology,
)

EXPECTED_KINDS = {
    "skill",
    "experience",
    "education",
    "project",
    "certification",
    "course",
    "language",
    "achievement",
    "interest",
    "artifact",
    "architecture_decision",
}


def test_registry_has_all_expected_kinds() -> None:
    assert set(GRAPH_REGISTRY.keys()) == EXPECTED_KINDS


def test_every_kind_has_sql_table_and_name_field() -> None:
    for kind, cfg in GRAPH_REGISTRY.items():
        assert cfg.sql_table, f"{kind} missing sql_table"
        assert cfg.name_field, f"{kind} missing name_field"
        assert cfg.kind == kind


def test_embedding_text_returns_str_for_all_kinds() -> None:
    sample = {
        "name": "X",
        "category": "tool",
        "level": "high",
        "organization": "Acme",
        "role": "Eng",
        "institution": "U",
        "title": "T",
        "description": "d",
        "code": "es",
    }
    for kind, cfg in GRAPH_REGISTRY.items():
        out = cfg.embedding_text(sample)
        assert isinstance(out, str), f"{kind} embedding_text not str"


def test_kinds_with_ontology() -> None:
    # Only skill + experience anchor to ESCO today.
    assert set(kinds_with_ontology()) == {"skill", "experience"}


def test_kinds_with_evidence_subset() -> None:
    evidence = set(kinds_with_evidence())
    assert evidence <= EXPECTED_KINDS
    assert "skill" in evidence


def test_crud_wiring_matches_registry() -> None:
    # The coherence dispatch wires CRUD/repo per kind — every registry
    # kind must have a wiring entry so upserts don't KeyError.
    from src.coherence.application.upsert_use_cases import _DISPATCH

    assert set(_DISPATCH.keys()) == EXPECTED_KINDS
