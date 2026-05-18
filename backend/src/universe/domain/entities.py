"""Universe entities.

Each entity is a lightweight dataclass — pure data + invariants. They are
*not* aggregate roots; the aggregate root is `Universe` (one per user), and
these are children. We model them as records because most operations are
CRUD; the heavier domain logic is in `Universe` (cross-entity invariants
like skill evidence, currentness, etc., later in v1).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, ClassVar, Literal
from uuid import UUID, uuid4

from src.shared.events import DomainEvent
from src.shared.value_objects import validate_cefr, validate_skill_level

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
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = field(default_factory=lambda: datetime.utcnow())
    deleted_at: datetime | None = None


# --- Education -----------------------------------------------------------


@dataclass
class Education(_Base):
    institution: str = ""
    degree: str | None = None
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = None
    highlights: list[str] = field(default_factory=list)
    gpa: float | None = None
    url: str | None = None

    @classmethod
    def create(cls, *, user_id: UUID, institution: str, **kw: Any) -> "Education":
        if not institution.strip():
            from src.shared.errors import ValidationError

            raise ValidationError("Institution is required for an education entry")
        return cls(id=uuid4(), user_id=user_id, institution=institution.strip(), **kw)

    def embedding_text(self) -> str:
        parts = [self.institution]
        if self.degree:
            parts.append(self.degree)
        if self.field_of_study:
            parts.append(self.field_of_study)
        if self.description:
            parts.append(self.description)
        parts.extend(self.highlights)
        return " — ".join(p for p in parts if p)


# --- Experience ----------------------------------------------------------


@dataclass
class Experience(_Base):
    organization: str = ""
    role: str = ""
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    location: dict[str, Any] | None = None
    employment_type: str | None = None
    modality: str | None = None
    description: str | None = None
    highlights: list[str] = field(default_factory=list)
    competences: list[str] = field(default_factory=list)
    url: str | None = None

    @classmethod
    def create(cls, *, user_id: UUID, organization: str, role: str, **kw: Any) -> "Experience":
        from src.shared.errors import ValidationError

        if not organization.strip() or not role.strip():
            raise ValidationError("Organization and role are required for an experience entry")
        return cls(
            id=uuid4(),
            user_id=user_id,
            organization=organization.strip(),
            role=role.strip(),
            **kw,
        )

    def embedding_text(self) -> str:
        parts = [self.role, "@", self.organization]
        if self.description:
            parts.append(self.description)
        parts.extend(self.highlights)
        parts.extend(self.competences)
        return " ".join(p for p in parts if p)


# --- Project -------------------------------------------------------------


@dataclass
class Project(_Base):
    name: str = ""
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    role: str | None = None
    project_type: str | None = None  # side, oss, entrepreneurship, work
    tech_stack: list[str] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    impact: str | None = None
    status: str | None = None
    url: str | None = None

    @classmethod
    def create(cls, *, user_id: UUID, name: str, **kw: Any) -> "Project":
        from src.shared.errors import ValidationError

        if not name.strip():
            raise ValidationError("Project name is required")
        return cls(id=uuid4(), user_id=user_id, name=name.strip(), **kw)

    def embedding_text(self) -> str:
        parts = [self.name]
        if self.description:
            parts.append(self.description)
        parts.extend(self.tech_stack)
        if self.impact:
            parts.append(self.impact)
        parts.extend(self.highlights)
        return " — ".join(p for p in parts if p)


# --- Skill ---------------------------------------------------------------


@dataclass
class Skill(_Base):
    name: str = ""
    category: str = "hard"  # hard, soft, tool, methodology
    level: str | None = None
    years: int | None = None
    last_used_year: int | None = None
    evidence_refs: list[str] = field(default_factory=list)

    @classmethod
    def create(cls, *, user_id: UUID, name: str, category: str = "hard", **kw: Any) -> "Skill":
        from src.shared.errors import ValidationError

        if not name.strip():
            raise ValidationError("Skill name is required")
        if category not in {"hard", "soft", "tool", "methodology"}:
            raise ValidationError(
                f"Invalid skill category {category!r}",
                details={"allowed": ["hard", "soft", "tool", "methodology"]},
            )
        if "level" in kw and kw["level"] is not None:
            validate_skill_level(kw["level"])
        return cls(
            id=uuid4(),
            user_id=user_id,
            name=name.strip(),
            category=category,
            **kw,
        )

    def embedding_text(self) -> str:
        bits = [self.name, self.category]
        if self.level:
            bits.append(self.level)
        return " ".join(bits)


# --- Certification -------------------------------------------------------


@dataclass
class Certification(_Base):
    name: str = ""
    issuer: str | None = None
    issued_on: date | None = None
    expires_on: date | None = None
    credential_id: str | None = None
    verification_url: str | None = None

    @classmethod
    def create(cls, *, user_id: UUID, name: str, **kw: Any) -> "Certification":
        from src.shared.errors import ValidationError

        if not name.strip():
            raise ValidationError("Certification name is required")
        return cls(id=uuid4(), user_id=user_id, name=name.strip(), **kw)

    def embedding_text(self) -> str:
        return " — ".join(p for p in [self.name, self.issuer or ""] if p)


# --- Course --------------------------------------------------------------


@dataclass
class Course(_Base):
    title: str = ""
    platform: str | None = None
    started_on: date | None = None
    completed_on: date | None = None
    duration_hours: int | None = None
    certificate_url: str | None = None

    @classmethod
    def create(cls, *, user_id: UUID, title: str, **kw: Any) -> "Course":
        from src.shared.errors import ValidationError

        if not title.strip():
            raise ValidationError("Course title is required")
        return cls(id=uuid4(), user_id=user_id, title=title.strip(), **kw)

    def embedding_text(self) -> str:
        return " — ".join(p for p in [self.title, self.platform or ""] if p)


# --- Language ------------------------------------------------------------


@dataclass
class Language(_Base):
    code: str = ""  # ISO 639-1
    name: str = ""
    level: str = "B2"
    certification: str | None = None

    @classmethod
    def create(cls, *, user_id: UUID, code: str, name: str, level: str, **kw: Any) -> "Language":
        from src.shared.errors import ValidationError

        if len(code) != 2 or not code.isalpha():
            raise ValidationError("Language code must be ISO 639-1 (2 letters)")
        validate_cefr(level)
        return cls(
            id=uuid4(),
            user_id=user_id,
            code=code.lower(),
            name=name,
            level=level,
            **kw,
        )

    def embedding_text(self) -> str:
        return f"{self.name} ({self.level})"


# --- Achievement ---------------------------------------------------------


@dataclass
class Achievement(_Base):
    title: str = ""
    achieved_on: date | None = None
    description: str | None = None
    context: str | None = None
    evidence_url: str | None = None

    @classmethod
    def create(cls, *, user_id: UUID, title: str, **kw: Any) -> "Achievement":
        from src.shared.errors import ValidationError

        if not title.strip():
            raise ValidationError("Achievement title is required")
        return cls(id=uuid4(), user_id=user_id, title=title.strip(), **kw)

    def embedding_text(self) -> str:
        return " — ".join(p for p in [self.title, self.description or ""] if p)


# --- Interest ------------------------------------------------------------


@dataclass
class Interest(_Base):
    name: str = ""
    description: str | None = None

    @classmethod
    def create(cls, *, user_id: UUID, name: str, **kw: Any) -> "Interest":
        from src.shared.errors import ValidationError

        if not name.strip():
            raise ValidationError("Interest name is required")
        return cls(id=uuid4(), user_id=user_id, name=name.strip(), **kw)

    def embedding_text(self) -> str:
        return self.name


# --- CareerPreferences (singleton per user) ------------------------------


@dataclass
class CareerPreferences:
    user_id: UUID
    status: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    contract_types: list[str] = field(default_factory=list)
    remote_preference: str | None = None
    open_to_relocate: bool | None = None
    working_areas: list[dict[str, Any]] = field(default_factory=list)
    perks_must_have: list[str] = field(default_factory=list)
    perks_nice_to_have: list[str] = field(default_factory=list)
    preferred_competences: list[str] = field(default_factory=list)
    discarded_competences: list[str] = field(default_factory=list)
    preferred_roles: list[str] = field(default_factory=list)
    discarded_roles: list[str] = field(default_factory=list)
    motivations: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.utcnow())
