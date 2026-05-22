"""Graph node dataclasses — typed views over AGE vertex properties.

These are small data carriers used by the application layer to avoid
slinging untyped dicts. They are NOT ORM models; AGE stores the vertices
inside the agtype JSON property bag.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class EntityNode:
    """A user-scoped entity vertex (skill, project, ...)."""

    id: UUID
    user_id: UUID
    kind: str  # "skill" | "project" | "experience" | ...
    created_at: datetime
    updated_at: datetime
    valid_from: datetime
    valid_to: datetime | None = None
    confidence: float | None = None
    source: str = "manual"
    embedding: list[float] | None = None
    esco_uri: str | None = None
    outlier_flag: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvidenceNode:
    """Reified n-ary relation. Connects ≥2 entities."""

    id: UUID
    user_id: UUID
    evidence_type: str  # "pr_merged" | "course_completion" | "blog_post" | ...
    title: str | None = None
    description: str | None = None
    source_url: str | None = None
    occurred_at: datetime | None = None
    created_at: datetime | None = None
    confidence: float | None = None
    source: str = "manual"


@dataclass(slots=True)
class SignalNode:
    """User × rubric_chunk overlay node."""

    id: UUID
    user_id: UUID
    rubric_chunk_id: UUID
    section_kind: str
    status: str  # "own" | "practice" | "aspire" | "teach" | "avoid"
    confidence: float
    last_reviewed_at: datetime | None = None
    notes: str | None = None
    source: str = "auto"


@dataclass(slots=True)
class EpisodeNode:
    """One chat session."""

    id: UUID
    user_id: UUID
    chat_session_id: str
    started_at: datetime
    ended_at: datetime | None = None
    summary: str | None = None
    embedding: list[float] | None = None


@dataclass(slots=True)
class CommunityNode:
    """A Leiden cluster within one user's universe."""

    id: UUID
    user_id: UUID
    label: str | None = None
    summary: str | None = None
    member_count: int = 0
    computed_at: datetime | None = None


@dataclass(slots=True)
class OccupationNode:
    """ESCO Occupation concept (read-only, shared)."""

    uri: str
    isco_code: str | None
    pref_label_es: str | None
    pref_label_en: str | None
    alt_labels_es: list[str] = field(default_factory=list)
    alt_labels_en: list[str] = field(default_factory=list)
    description_es: str | None = None
    description_en: str | None = None
    embedding: list[float] | None = None


@dataclass(slots=True)
class EscoSkillNode:
    """ESCO Skill/Competence concept (read-only, shared)."""

    uri: str
    skill_type: str | None  # "skill/competence" | "knowledge"
    pref_label_es: str | None
    pref_label_en: str | None
    alt_labels_es: list[str] = field(default_factory=list)
    alt_labels_en: list[str] = field(default_factory=list)
    description_es: str | None = None
    description_en: str | None = None
    embedding: list[float] | None = None
