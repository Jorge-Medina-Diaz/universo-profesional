"""Declarative entity-resolution config per universe entity kind.

The ER pipeline does: blocking → pairwise matching → clustering → provenance.
These configs supply the per-kind blocking strategies and match thresholds.
Field-level merging of the surviving entity is owned separately by
``domain/merge_rules.py`` (→ ``MergePlan.merged_payload`` → ``crud.update``),
not here.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErConfig:
    kind: str
    blocking_keys: tuple[str, ...]
    """Ordered list of blocking strategies to try.
    Available: "name_exact", "name_phonetic", "embedding_nearest", "esco_uri"."""
    matching_threshold: float
    """Composite score above which two entities are considered a match."""
    ambiguous_low: float
    """Composite score below which the pair is discarded; between
    ambiguous_low and matching_threshold → ambiguous (needs user)."""


# ---------------------------------------------------------------------------
# Per-kind configs
# ---------------------------------------------------------------------------
ER_REGISTRY: dict[str, ErConfig] = {
    "skill": ErConfig(
        kind="skill",
        blocking_keys=("name_exact", "name_phonetic", "embedding_nearest", "esco_uri"),
        matching_threshold=0.88,
        ambiguous_low=0.75,
    ),
    "experience": ErConfig(
        kind="experience",
        blocking_keys=("name_exact", "name_phonetic", "embedding_nearest"),
        matching_threshold=0.82,
        ambiguous_low=0.70,
    ),
    "education": ErConfig(
        kind="education",
        blocking_keys=("name_exact", "embedding_nearest"),
        matching_threshold=0.85,
        ambiguous_low=0.72,
    ),
    "project": ErConfig(
        kind="project",
        blocking_keys=("name_exact", "name_phonetic", "embedding_nearest"),
        matching_threshold=0.82,
        ambiguous_low=0.70,
    ),
    "certification": ErConfig(
        kind="certification",
        blocking_keys=("name_exact", "name_phonetic", "embedding_nearest"),
        matching_threshold=0.88,
        ambiguous_low=0.75,
    ),
    "course": ErConfig(
        kind="course",
        blocking_keys=("name_exact", "embedding_nearest"),
        matching_threshold=0.85,
        ambiguous_low=0.72,
    ),
    "language": ErConfig(
        kind="language",
        blocking_keys=("name_exact", "esco_uri"),
        matching_threshold=0.95,
        ambiguous_low=0.90,
    ),
    "achievement": ErConfig(
        kind="achievement",
        blocking_keys=("name_exact", "embedding_nearest"),
        matching_threshold=0.85,
        ambiguous_low=0.72,
    ),
    "interest": ErConfig(
        kind="interest",
        blocking_keys=("name_exact", "name_phonetic"),
        matching_threshold=0.90,
        ambiguous_low=0.80,
    ),
}


def config_for(kind: str) -> ErConfig | None:
    return ER_REGISTRY.get(kind)
