"""Smoke tests for coherence_v2 pure structure (no DB).

The heavy paths (ESCO linking, edge writes) are DB/AGE-backed and covered
manually + by the integration suite. Here we lock down the static edge
map + the public surface so a refactor can't silently drop a relation
kind or rename a public function.
"""
from __future__ import annotations

from src.coherence.application import coherence_v2
from src.graph.domain import schema


def test_derived_from_edge_map_covers_expected_keys() -> None:
    keys = set(coherence_v2._DERIVED_FROM_EDGES.keys())
    assert "derived_from_project_id" in keys
    assert "derived_from_experience_id" in keys
    # Every mapped edge type must be a real schema constant + DERIVED_FROM.
    for edge_type, _kind in coherence_v2._DERIVED_FROM_EDGES.values():
        assert edge_type == schema.DERIVED_FROM


def test_public_surface_is_stable() -> None:
    # These are imported by upsert_use_cases / curator / graph_router —
    # renaming them silently would break the wiring.
    for name in (
        "post_upsert",
        "resolve_quarantine",
        "flag_outliers_for_user",
    ):
        assert hasattr(coherence_v2, name), f"missing coherence_v2.{name}"


def test_schema_edge_constants_present() -> None:
    # The edges materialised by coherence_v2 must exist in the schema.
    for edge in ("DERIVED_FROM", "USES_TECH", "PART_OF", "SUPERSEDES"):
        assert hasattr(schema, edge)
