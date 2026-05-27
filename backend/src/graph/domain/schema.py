"""Graph schema constants — vertex labels, edge types, AGE graph names.

The schema is intentionally narrow:
  • Personal graph holds one logical universe per user, multi-tenant via
    the `user_id` property on every vertex and edge.
  • Ontology graph holds the shared ESCO + schema.org backbone; reads
    only, write-locked at runtime.

Edges follow a consistent directionality (verbs read from the subject):
    (:Entity {kind: "skill"}) <-[:DEMONSTRATES]- (:Evidence) -[:OCCURRED_IN]-> (:Entity {kind: "experience"})

When in doubt, look at the docstring on each edge: the arrow direction
documents the canonical source → target.
"""
from __future__ import annotations

from typing import Final, Literal

# ---------------------------------------------------------------------------
# Graph names
# ---------------------------------------------------------------------------

GRAPH_PERSONAL: Final = "universe_personal"
GRAPH_ONTOLOGY: Final = "universe_ontology"


# ---------------------------------------------------------------------------
# Vertex labels (personal graph)
# ---------------------------------------------------------------------------

# v1 generic label — kept for backward compatibility during the N→R
# migration window. New code should use the typed labels below.
ENTITY: Final = "Entity"
"""Generic user entity (legacy). The `kind` property distinguishes types.
New writes use the typed labels below; reads query both."""

# v2 typed labels — one per entity kind for expressive Cypher and
# schema-level query planning (AGE can index per-label).
EXPERIENCE: Final = "Experience"
EDUCATION: Final = "Education"
SKILL: Final = "Skill"
PROJECT: Final = "Project"
CERTIFICATION: Final = "Certification"
COURSE: Final = "Course"
LANGUAGE: Final = "Language"
ACHIEVEMENT: Final = "Achievement"
INTEREST: Final = "Interest"
ARTIFACT: Final = "Artifact"
ARCHITECTURE_DECISION: Final = "ArchitectureDecision"

# Mapping from canonical kind string → graph label.
KIND_TO_LABEL: Final[dict[str, str]] = {
    "experience": EXPERIENCE,
    "education": EDUCATION,
    "skill": SKILL,
    "project": PROJECT,
    "certification": CERTIFICATION,
    "course": COURSE,
    "language": LANGUAGE,
    "achievement": ACHIEVEMENT,
    "interest": INTEREST,
    "artifact": ARTIFACT,
    "architecture_decision": ARCHITECTURE_DECISION,
}

EVIDENCE: Final = "Evidence"
"""Reified n-ary relation. Replaces the polymorphic `evidences` table —
edges from an Evidence to ≥2 Entity nodes encode hyperedge semantics in
a multigraph-friendly way."""

SIGNAL: Final = "Signal"
"""User × rubric_chunk overlay. Replaces `user_rubric_signals` rows."""

EPISODE: Final = "Episode"
"""Chat session lifetime. Connects every entity touched during the
session via :TOUCHED_IN."""

COMMUNITY: Final = "Community"
"""Leiden cluster within a user's universe. Surfaced in the UI's
graph-lens LOD and used by the (deferred) global retrieval lane."""

GOAL: Final = "Goal"
"""Mirror of the existing Goal entity, lifted into the graph so that
goal → skill / project decomposition edges can be expressed."""


# ---------------------------------------------------------------------------
# Vertex labels (ontology graph)
# ---------------------------------------------------------------------------

OCCUPATION: Final = "Occupation"
"""ESCO Occupation concept (≈3 000 nodes)."""

ESCO_SKILL: Final = "EscoSkill"
"""ESCO Skill/Competence concept (≈14 000 nodes)."""

ISCO_GROUP: Final = "ISCOGroup"
"""ISCO-08 occupation classification group (numeric code + label)."""


# ---------------------------------------------------------------------------
# Edge types (relationship types). Convention: verb in the subject voice.
# ---------------------------------------------------------------------------

# Personal evidence / relation edges
DEMONSTRATES: Final = "DEMONSTRATES"
"""Evidence → Skill — this evidence demonstrates this skill."""

PART_OF: Final = "PART_OF"
"""Project|Evidence → Experience — happened during this engagement."""

USES_TECH: Final = "USES_TECH"
"""Project|Artifact|Experience → Skill — uses this technology/skill."""

OCCURRED_IN: Final = "OCCURRED_IN"
"""Evidence → Experience — temporal anchor of the evidence."""

PRODUCED: Final = "PRODUCED"
"""Evidence → Artifact — produced this artifact."""

EVIDENCES_SIGNAL: Final = "EVIDENCES_SIGNAL"
"""Entity → Signal — backs this rubric signal as evidence."""

LINKS_TO_ESCO: Final = "LINKS_TO_ESCO"
"""Entity → EscoSkill|Occupation — anchor to the ontology backbone."""

SUPERSEDES: Final = "SUPERSEDES"
"""ArchitectureDecision → ArchitectureDecision — this ADR replaces that one."""

DERIVED_FROM: Final = "DERIVED_FROM"
"""Skill → Project|Course — provenance of how this skill was acquired."""

TOUCHED_IN: Final = "TOUCHED_IN"
"""Entity → Episode — this node was created/modified during that session."""

MEMBER_OF: Final = "MEMBER_OF"
"""Entity → Community — Leiden cluster membership."""

RELATED_TO: Final = "RELATED_TO"
"""Generic edge for user-asserted relations that don't fit a typed verb.
Carries a `relation_label` property describing the user's wording."""

# Ontology edges (in universe_ontology)
SKOS_BROADER: Final = "SKOS_BROADER"
SKOS_NARROWER: Final = "SKOS_NARROWER"
SKOS_RELATED: Final = "SKOS_RELATED"
ESSENTIAL_FOR: Final = "ESSENTIAL_FOR"
"""EscoSkill → Occupation — essential skill of the occupation."""
OPTIONAL_FOR: Final = "OPTIONAL_FOR"
"""EscoSkill → Occupation — optional skill of the occupation."""
ISCO_GROUP_OF: Final = "ISCO_GROUP_OF"
"""Occupation → ISCOGroup — classification anchor."""


# ---------------------------------------------------------------------------
# Property conventions
# ---------------------------------------------------------------------------

# Every personal vertex carries these properties (in addition to kind-specific)
BASE_VERTEX_PROPS: Final = (
    "id",            # mirrors the SQL primary key — bridges graph ↔ tables
    "user_id",       # multi-tenant filter
    "kind",          # entity kind for :Entity, otherwise the label itself
    "created_at",
    "updated_at",
    "valid_from",
    "valid_to",      # NULL means active; set when soft-deleted/superseded
    "confidence",
    "source",        # "manual" | "import" | "agent"
    "embedding",     # mirror of the SQL embedding for graph-local similarity
)

# Every edge carries these — Graphiti-style temporal model
BASE_EDGE_PROPS: Final = (
    "valid_from",
    "valid_to",
    "confidence",
    "source",
)


# ---------------------------------------------------------------------------
# Entity kinds (mirror of universe.domain.entities.EntityType)
# ---------------------------------------------------------------------------

EntityKind = Literal[
    "skill",
    "experience",
    "project",
    "education",
    "certification",
    "course",
    "language",
    "achievement",
    "interest",
    "artifact",
    "architecture_decision",
]

ENTITY_KINDS: Final[tuple[str, ...]] = (
    "skill",
    "experience",
    "project",
    "education",
    "certification",
    "course",
    "language",
    "achievement",
    "interest",
    "artifact",
    "architecture_decision",
)
