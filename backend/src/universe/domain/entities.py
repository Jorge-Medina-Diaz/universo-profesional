"""Universe entities.

Each entity is a lightweight dataclass — pure data + invariants. They are
*not* aggregate roots; the aggregate root is `Universe` (one per user), and
these are children. We model them as records because most operations are
CRUD; the heavier domain logic is in `Universe` (cross-entity invariants
like skill evidence, currentness, etc., later in v1).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, ClassVar, Literal
from uuid import UUID

from src.shared.events import DomainEvent

EntityType = Literal[
    "education",
    "experience",
    "project",
    "skill",
    "certification",
    "course",
    "language",
    "achievement",
    "interest",
    "artifact",
    "architecture_decision",
]


@dataclass(frozen=True, kw_only=True)
class EntryAdded(DomainEvent):
    event_type: ClassVar[str] = "universe.entry_added"
    entity_type: str = ""
    entity_id_str: str = ""


@dataclass(frozen=True, kw_only=True)
class EntryUpdated(DomainEvent):
    event_type: ClassVar[str] = "universe.entry_updated"
    entity_type: str = ""
    entity_id_str: str = ""


@dataclass(frozen=True, kw_only=True)
class EntryRemoved(DomainEvent):
    event_type: ClassVar[str] = "universe.entry_removed"
    entity_type: str = ""
    entity_id_str: str = ""


# --- Common base ---------------------------------------------------------


@dataclass
class _Base:
    id: UUID
    user_id: UUID
    source: str = "manual"
    visibility: str = "public"
    confidence: float | None = None
    source_metadata: dict[str, Any] | None = None
    last_reviewed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None


# --- Shared constants ----------------------------------------------------


CANONICAL_AREAS = (
    "backend",
    "frontend",
    "fullstack",
    "devops",
    "mobile",
    "ai_ml",
    "data_eng",
    "security",
    "llm_agents",
    "cloud",
    "platform",
    "other",
)

# Backward-compatible re-exports — previous code imported directly from this module.
from src.universe.domain.achievement import Achievement  # noqa: E402,F401
from src.universe.domain.architecture_decision import (  # noqa: E402,F401
    ADR_STATUSES,
    ArchitectureDecision,
)
from src.universe.domain.artifact import Artifact, ArtifactType  # noqa: E402,F401
from src.universe.domain.career import (  # noqa: E402,F401
    AreaStrength,
    CareerPreferences,
    ShapeType,
)
from src.universe.domain.certification import Certification  # noqa: E402,F401
from src.universe.domain.course import Course  # noqa: E402,F401
from src.universe.domain.education import Education  # noqa: E402,F401
from src.universe.domain.experience import Experience  # noqa: E402,F401
from src.universe.domain.interest import Interest  # noqa: E402,F401
from src.universe.domain.language import Language  # noqa: E402,F401
from src.universe.domain.project import Project  # noqa: E402,F401
from src.universe.domain.rubric_signal import (  # noqa: E402,F401
    SIGNAL_SECTION_KINDS,
    SIGNAL_STATUSES,
    UserRubricSignal,
)
from src.universe.domain.skill import Skill  # noqa: E402,F401
from src.universe.domain.skill_stack import SkillStack  # noqa: E402,F401
