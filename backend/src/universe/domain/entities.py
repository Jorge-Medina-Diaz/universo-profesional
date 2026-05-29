"""Universe entities.

Each entity is a lightweight dataclass — pure data + invariants. They are
*not* aggregate roots; the aggregate root is `Universe` (one per user), and
these are children. We model them as records because most operations are
CRUD; the heavier domain logic is in `Universe` (cross-entity invariants
like skill evidence, currentness, etc., later in v1).
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field, fields as _dc_fields
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

    def __post_init__(self) -> None:
        # JSON bodies and importers carry dates as ISO *strings* (e.g.
        # "2020-01-01"). Dataclasses don't coerce types, so without this an
        # entity's `date`-typed field reaches asyncpg's DATE binding as a raw
        # str and crashes with "'str' object has no attribute 'toordinal'"
        # (a 500 on every experience/education/… add that includes a date).
        # Coerce date-only fields here so every path — API, LinkedIn ZIP,
        # JSON Resume, CV PDF, MCP — is covered in one place.
        for name in _date_only_field_names(type(self)):
            value = getattr(self, name)
            if isinstance(value, str):
                setattr(self, name, _to_date(value))


# --- Date coercion helpers (shared by every entity via _Base) ------------

_DATE_FIELDS_CACHE: dict[type, tuple[str, ...]] = {}


def _date_only_field_names(cls: type) -> tuple[str, ...]:
    """Names of dataclass fields typed `date` (NOT `datetime`). Cached per class.

    `datetime` is a subclass of `date`, so we compare by identity to keep the
    timestamp fields (created_at, …) out — those are never user-supplied strings.
    """
    cached = _DATE_FIELDS_CACHE.get(cls)
    if cached is not None:
        return cached
    import typing

    try:
        hints = typing.get_type_hints(cls)
    except Exception:
        hints = {}
    names: list[str] = []
    for f in _dc_fields(cls):
        hint = hints.get(f.name)
        args = typing.get_args(hint)
        candidates = args if args else (hint,)
        if any(c is _dt.date for c in candidates):
            names.append(f.name)
    result = tuple(names)
    _DATE_FIELDS_CACHE[cls] = result
    return result


def _to_date(value: str) -> _dt.date | None:
    """Parse an ISO date string → `date`. Empty → None; invalid → ValidationError.

    Accepts a leading full ISO datetime too (we keep the date part). Raising
    keeps bad input *visible*: the CRUD layer catches ValidationError and the
    row is reported/skipped instead of failing silently or 500-ing.
    """
    s = value.strip()
    if not s:
        return None
    try:
        return _dt.date.fromisoformat(s[:10])
    except ValueError as exc:
        from src.shared.errors import ValidationError

        raise ValidationError(f"Invalid date value: {value!r}") from exc


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
