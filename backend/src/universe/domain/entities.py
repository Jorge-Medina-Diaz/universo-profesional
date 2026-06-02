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
from decimal import Decimal
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
        # JSON bodies and importers carry typed values as *strings* (dates like
        # "2020-01-01", numbers like "5", uuids). Dataclasses don't coerce, and
        # asyncpg rejects a str where a date/int/uuid is expected (e.g. "'str'
        # object has no attribute 'toordinal'" → a 500 on any add/merge with a
        # date). Coerce EVERY field to its declared type here so CREATE is
        # type-safe on every path (API, LinkedIn ZIP, JSON Resume, CV PDF, MCP);
        # the UPDATE/merge path mirrors this via _EntityCrud._apply_patch.
        apply_field_coercion(self)


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
    # Full ISO date (or a leading ISO datetime — keep the date part).
    try:
        return _dt.date.fromisoformat(s[:10])
    except ValueError:
        pass
    # Partial dates from CVs/imports: "2022" or "2022-07" → default missing
    # parts to 1 (real-world experience/education ranges are often year-month).
    import re

    m = re.match(r"^(\d{4})(?:-(\d{1,2}))(?:-(\d{1,2}))?$|^(\d{4})$", s)
    if m:
        year = int(m.group(1) or m.group(4))
        month = int(m.group(2) or 1)
        day = int(m.group(3) or 1)
        try:
            return _dt.date(year, month, day)
        except ValueError:
            pass
    from src.shared.errors import ValidationError

    raise ValidationError(f"Invalid date value: {value!r}")


# --- Type-driven field coercion (shared by create + update) --------------
#
# asyncpg binds Python objects directly: a str where a date/datetime/int/uuid
# is expected raises a DataError (a 500). These coercers convert from the
# strings that JSON/importers carry to the declared column type. Each is
# IDEMPOTENT — a value already of the right type (or None) passes through
# unchanged. Invalid input raises ValidationError (→ 422, visible, not a 500).

_COERCERS_CACHE: dict[type, dict[str, Any]] = {}


def _to_date_or_none(v: Any) -> Any:
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    if isinstance(v, str):
        return _to_date(v)
    return v


def _to_datetime(v: Any) -> Any:
    if isinstance(v, _dt.datetime):
        return v
    if isinstance(v, _dt.date):
        return _dt.datetime(v.year, v.month, v.day, tzinfo=UTC)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return _dt.datetime.fromisoformat(s)
        except ValueError as exc:
            from src.shared.errors import ValidationError

            raise ValidationError(f"Invalid datetime value: {v!r}") from exc
    return v


def _to_int(v: Any) -> Any:
    if v is None or isinstance(v, bool) or isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return int(s)
        except ValueError:
            try:
                return int(float(s))
            except ValueError as exc:
                from src.shared.errors import ValidationError

                raise ValidationError(f"Invalid integer value: {v!r}") from exc
    return v


def _to_float(v: Any) -> Any:
    if v is None or isinstance(v, bool) or isinstance(v, (int, float, Decimal)):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError as exc:
            from src.shared.errors import ValidationError

            raise ValidationError(f"Invalid number value: {v!r}") from exc
    return v


def _to_bool(v: Any) -> Any:
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"true", "1", "yes", "y"}:
            return True
        if s in {"false", "0", "no", "n", ""}:
            return False
    return v


def _to_uuid(v: Any) -> Any:
    if v is None or isinstance(v, UUID):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return UUID(s)
        except ValueError as exc:
            from src.shared.errors import ValidationError

            raise ValidationError(f"Invalid id value: {v!r}") from exc
    return v


def _field_coercers(cls: type) -> dict[str, Any]:
    """Map each dataclass field → a coercer chosen by its annotation. Cached.

    Covers date/datetime/int/float/Decimal/bool/UUID; str/dict/list are left
    untouched. `bool` is checked before `int` (bool ⊂ int); `datetime` before
    `date` (datetime ⊂ date). Identity comparison keeps the match exact.
    """
    cached = _COERCERS_CACHE.get(cls)
    if cached is not None:
        return cached
    import typing

    try:
        hints = typing.get_type_hints(cls)
    except Exception:
        hints = {}
    out: dict[str, Any] = {}
    for f in _dc_fields(cls):
        hint = hints.get(f.name)
        args = typing.get_args(hint)
        candidates = args if args else (hint,)
        if any(c is _dt.datetime for c in candidates):
            out[f.name] = _to_datetime
        elif any(c is _dt.date for c in candidates):
            out[f.name] = _to_date_or_none
        elif any(c is bool for c in candidates):
            out[f.name] = _to_bool
        elif any(c is int for c in candidates):
            out[f.name] = _to_int
        elif any(c is float or c is Decimal for c in candidates):
            out[f.name] = _to_float
        elif any(c is UUID for c in candidates):
            out[f.name] = _to_uuid
    _COERCERS_CACHE[cls] = out
    return out


def apply_field_coercion(obj: Any) -> None:
    """Coerce every typed field on a dataclass instance in place (idempotent)."""
    for name, coerce in _field_coercers(type(obj)).items():
        value = getattr(obj, name)
        new = coerce(value)
        if new is not value:
            setattr(obj, name, new)


def coerce_patch(cls: type, patch: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of `patch` with each known field coerced to its declared
    type. Used by the UPDATE/merge path so it's as type-safe as create."""
    coercers = _field_coercers(cls)
    out: dict[str, Any] = {}
    for k, v in patch.items():
        out[k] = coercers[k](v) if k in coercers else v
    return out


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
