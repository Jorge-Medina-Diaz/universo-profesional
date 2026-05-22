"""GraphRegistry — typed, ontology-aware view of every entity kind.

Sprint G introduced `ENTITY_REGISTRY` in `coherence/upsert_use_cases.py`
as a flat dispatch table. Sprint N upgrades it: the registry now carries
the metadata needed for graph + ontology operations (ESCO link target,
quarantine policy, evidence support) and lives in the graph module so
coherence v2 can read it without depending on the legacy upsert path.

Each entry describes one entity kind. The kind name matches the
`Entity.kind` property in AGE *and* the `entity_type` column used by
the legacy SQL tables — they share the same vocabulary throughout.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

OntoLinkKind = Literal["skill", "occupation"] | None


@dataclass(frozen=True)
class GraphNodeKind:
    """Self-describing entry for one entity kind in the graph universe."""

    kind: str
    """Canonical name — used as the `kind` property on :Entity vertices
    and as the `entity_type` column for legacy tables."""

    sql_table: str
    """Authoritative SQL table holding the row's properties. The graph
    only carries id + relations + lightweight metadata; full property
    rows live in this table until Sprint R cutover."""

    name_field: str
    """Field used for case-insensitive exact-match lookup during dedup."""

    embedding_text: Callable[[dict[str, Any]], str]
    """Builds the text we embed for dense similarity. Identical contract
    to Sprint G's registry to ease the migration."""

    onto_link_kind: OntoLinkKind = None
    """If non-None, the coherence engine attempts ESCO entity-linking
    against this concept type. "skill" maps to :EscoSkill, "occupation"
    maps to :Occupation. None means the kind has no ontology anchor."""

    supports_evidence: bool = False
    """True when the kind accepts `derived_from_*` payload keys; the
    coherence engine materialises them as :Evidence / :DEMONSTRATES
    edges."""

    supports_stale: bool = True
    """True when the curator may mark this kind stale after the review
    window expires."""

    review_window_days: int = 365
    """Default time before curator nudges the user to confirm relevance."""

    auto_dedup: bool = True
    """When True, the coherence engine uses semantic similarity (vector
    cosine ≥ AUTO_MERGE_THRESHOLD) to merge silently. When False, only
    exact-name and ESCO-URI matches deduplicate; everything else is
    treated as a separate entity (e.g. languages, where two CEFR levels
    of the same ISO code are obviously the same row)."""


def _skill_text(p: dict[str, Any]) -> str:
    return f"{p.get('name','')} {p.get('category','')} {p.get('level','')}".strip()


def _experience_text(p: dict[str, Any]) -> str:
    return (
        f"{p.get('role','')} @ {p.get('organization','')} "
        f"{p.get('description','') or ''} "
        f"{' '.join(p.get('competences') or [])}"
    ).strip()


def _education_text(p: dict[str, Any]) -> str:
    return (
        f"{p.get('institution','')} {p.get('degree','')} "
        f"{p.get('field_of_study','')} {p.get('description','') or ''}"
    ).strip()


def _project_text(p: dict[str, Any]) -> str:
    return (
        f"{p.get('name','')} {p.get('description','') or ''} "
        f"{' '.join(p.get('tech_stack') or [])} "
        f"{' '.join(p.get('highlights') or [])}"
    ).strip()


def _cert_text(p: dict[str, Any]) -> str:
    return f"{p.get('name','')} {p.get('issuer','') or ''}".strip()


def _course_text(p: dict[str, Any]) -> str:
    return f"{p.get('title','')} {p.get('platform','') or ''}".strip()


def _language_text(p: dict[str, Any]) -> str:
    return f"{p.get('code','')} {p.get('name','') or ''} {p.get('level','') or ''}".strip()


def _achievement_text(p: dict[str, Any]) -> str:
    return f"{p.get('title','')} {p.get('description','') or ''}".strip()


def _interest_text(p: dict[str, Any]) -> str:
    return f"{p.get('name','')} {p.get('description','') or ''}".strip()


def _artifact_text(p: dict[str, Any]) -> str:
    return " — ".join(
        s
        for s in (
            p.get("type"),
            p.get("title"),
            p.get("description"),
            p.get("venue"),
        )
        if s
    )


def _adr_text(p: dict[str, Any]) -> str:
    return " — ".join(
        s
        for s in (p.get("title"), p.get("context"), p.get("decision"))
        if s
    )


GRAPH_REGISTRY: dict[str, GraphNodeKind] = {
    "skill": GraphNodeKind(
        kind="skill",
        sql_table="skills",
        name_field="name",
        embedding_text=_skill_text,
        onto_link_kind="skill",
        supports_evidence=True,
    ),
    "experience": GraphNodeKind(
        kind="experience",
        sql_table="experiences",
        name_field="organization",
        embedding_text=_experience_text,
        onto_link_kind="occupation",
        review_window_days=730,
    ),
    "education": GraphNodeKind(
        kind="education",
        sql_table="educations",
        name_field="institution",
        embedding_text=_education_text,
        review_window_days=1825,
        auto_dedup=False,  # different start_date → different entry
    ),
    "project": GraphNodeKind(
        kind="project",
        sql_table="projects",
        name_field="name",
        embedding_text=_project_text,
        supports_evidence=True,
        review_window_days=365,
    ),
    "certification": GraphNodeKind(
        kind="certification",
        sql_table="certifications",
        name_field="name",
        embedding_text=_cert_text,
        review_window_days=730,
    ),
    "course": GraphNodeKind(
        kind="course",
        sql_table="courses",
        name_field="title",
        embedding_text=_course_text,
        review_window_days=730,
    ),
    "language": GraphNodeKind(
        kind="language",
        sql_table="languages",
        name_field="code",
        embedding_text=_language_text,
        review_window_days=1825,
        auto_dedup=False,
    ),
    "achievement": GraphNodeKind(
        kind="achievement",
        sql_table="achievements",
        name_field="title",
        embedding_text=_achievement_text,
        review_window_days=730,
    ),
    "interest": GraphNodeKind(
        kind="interest",
        sql_table="interests",
        name_field="name",
        embedding_text=_interest_text,
        review_window_days=365,
    ),
    "artifact": GraphNodeKind(
        kind="artifact",
        sql_table="artifacts",
        name_field="title",
        embedding_text=_artifact_text,
        supports_evidence=True,
        review_window_days=730,
    ),
    "architecture_decision": GraphNodeKind(
        kind="architecture_decision",
        sql_table="architecture_decisions",
        name_field="title",
        embedding_text=_adr_text,
        review_window_days=365,
    ),
}
"""Single source of truth for every entity kind the graph universe knows.

Adding a kind: append one entry. The coherence engine, the curator, the
retrieval seed picker and the signal extractor all iterate this map; no
parallel whitelists exist."""


def kinds_with_ontology() -> list[str]:
    """Kinds that can be entity-linked to the ESCO backbone."""
    return [k for k, v in GRAPH_REGISTRY.items() if v.onto_link_kind is not None]


def kinds_with_evidence() -> list[str]:
    return [k for k, v in GRAPH_REGISTRY.items() if v.supports_evidence]
