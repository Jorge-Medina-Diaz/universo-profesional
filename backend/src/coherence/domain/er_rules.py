"""Declarative entity-resolution rules per universe entity kind.

Sprint R replaces the single-threshold semantic matcher with a full ER
pipeline: blocking → pairwise matching → clustering → merge → provenance.
These rules configure the merge and matching strategies per kind.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


FieldStrategy = Literal[
    "longest_non_null",
    "earliest",
    "latest",
    "max",
    "max_ranked",
    "union",
    "esco_preferred",
    "concatenate_unique",
    "preserve_existing",
]


@dataclass(frozen=True)
class FieldRule:
    field: str
    strategy: FieldStrategy
    ranking: dict[str, int] | None = None
    """Required when strategy="max_ranked"."""


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
    field_rules: tuple[FieldRule, ...]
    """How to resolve each field when merging a cluster."""


# ---------------------------------------------------------------------------
# Rankings reused by max_ranked
# ---------------------------------------------------------------------------
_SKILL_LEVEL_RANK = {"basic": 1, "intermediate": 2, "high": 3, "expert": 4}
_CEFR_RANK = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6, "native": 7}

# ---------------------------------------------------------------------------
# Per-kind configs
# ---------------------------------------------------------------------------
ER_REGISTRY: dict[str, ErConfig] = {
    "skill": ErConfig(
        kind="skill",
        blocking_keys=("name_exact", "name_phonetic", "embedding_nearest", "esco_uri"),
        matching_threshold=0.88,
        ambiguous_low=0.75,
        field_rules=(
            FieldRule("name", "esco_preferred"),
            FieldRule("level", "max_ranked", ranking=_SKILL_LEVEL_RANK),
            FieldRule("years", "max"),
            FieldRule("last_used_year", "max"),
            FieldRule("category", "preserve_existing"),
            FieldRule("esco_uri", "esco_preferred"),
        ),
    ),
    "experience": ErConfig(
        kind="experience",
        blocking_keys=("name_exact", "name_phonetic", "embedding_nearest"),
        matching_threshold=0.82,
        ambiguous_low=0.70,
        field_rules=(
            FieldRule("organization", "longest_non_null"),
            FieldRule("role", "longest_non_null"),
            FieldRule("start_date", "earliest"),
            FieldRule("end_date", "latest"),
            FieldRule("description", "concatenate_unique"),
            FieldRule("highlights", "union"),
            FieldRule("competences", "union"),
            FieldRule("esco_uri", "esco_preferred"),
        ),
    ),
    "education": ErConfig(
        kind="education",
        blocking_keys=("name_exact", "embedding_nearest"),
        matching_threshold=0.85,
        ambiguous_low=0.72,
        field_rules=(
            FieldRule("institution", "longest_non_null"),
            FieldRule("degree", "longest_non_null"),
            FieldRule("field_of_study", "longest_non_null"),
            FieldRule("start_date", "earliest"),
            FieldRule("end_date", "latest"),
            FieldRule("description", "concatenate_unique"),
            FieldRule("highlights", "union"),
        ),
    ),
    "project": ErConfig(
        kind="project",
        blocking_keys=("name_exact", "name_phonetic", "embedding_nearest"),
        matching_threshold=0.82,
        ambiguous_low=0.70,
        field_rules=(
            FieldRule("name", "longest_non_null"),
            FieldRule("description", "concatenate_unique"),
            FieldRule("role", "longest_non_null"),
            FieldRule("tech_stack", "union"),
            FieldRule("highlights", "union"),
            FieldRule("impact", "concatenate_unique"),
            FieldRule("url", "preserve_existing"),
        ),
    ),
    "certification": ErConfig(
        kind="certification",
        blocking_keys=("name_exact", "name_phonetic", "embedding_nearest"),
        matching_threshold=0.88,
        ambiguous_low=0.75,
        field_rules=(
            FieldRule("name", "longest_non_null"),
            FieldRule("issuer", "longest_non_null"),
            FieldRule("issued_on", "earliest"),
            FieldRule("expires_on", "latest"),
            FieldRule("credential_id", "preserve_existing"),
            FieldRule("verification_url", "preserve_existing"),
        ),
    ),
    "course": ErConfig(
        kind="course",
        blocking_keys=("name_exact", "embedding_nearest"),
        matching_threshold=0.85,
        ambiguous_low=0.72,
        field_rules=(
            FieldRule("title", "longest_non_null"),
            FieldRule("platform", "longest_non_null"),
            FieldRule("started_on", "earliest"),
            FieldRule("completed_on", "preserve_existing"),
            FieldRule("duration_hours", "max"),
        ),
    ),
    "language": ErConfig(
        kind="language",
        blocking_keys=("name_exact", "esco_uri"),
        matching_threshold=0.95,
        ambiguous_low=0.90,
        field_rules=(
            FieldRule("code", "preserve_existing"),
            FieldRule("name", "preserve_existing"),
            FieldRule("level", "max_ranked", ranking=_CEFR_RANK),
            FieldRule("certification", "preserve_existing"),
        ),
    ),
    "achievement": ErConfig(
        kind="achievement",
        blocking_keys=("name_exact", "embedding_nearest"),
        matching_threshold=0.85,
        ambiguous_low=0.72,
        field_rules=(
            FieldRule("title", "longest_non_null"),
            FieldRule("achieved_on", "earliest"),
            FieldRule("description", "concatenate_unique"),
            FieldRule("context", "concatenate_unique"),
            FieldRule("evidence_url", "preserve_existing"),
        ),
    ),
    "interest": ErConfig(
        kind="interest",
        blocking_keys=("name_exact", "name_phonetic"),
        matching_threshold=0.90,
        ambiguous_low=0.80,
        field_rules=(
            FieldRule("name", "longest_non_null"),
            FieldRule("description", "concatenate_unique"),
        ),
    ),
}


def config_for(kind: str) -> ErConfig | None:
    return ER_REGISTRY.get(kind)
