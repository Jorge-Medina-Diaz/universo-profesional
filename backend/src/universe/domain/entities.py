"""Universe entities.

Each entity is a lightweight dataclass — pure data + invariants. They are
*not* aggregate roots; the aggregate root is `Universe` (one per user), and
these are children. We model them as records because most operations are
CRUD; the heavier domain logic is in `Universe` (cross-entity invariants
like skill evidence, currentness, etc., later in v1).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
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
    def create(cls, *, user_id: UUID, institution: str, **kw: Any) -> Education:
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
    industry_sector: str | None = None  # finance, healthcare, ecommerce, govtech, …
    seniority_level: str | None = None  # junior|mid|senior|staff|principal|exec

    @classmethod
    def create(cls, *, user_id: UUID, organization: str, role: str, **kw: Any) -> Experience:
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
    domain_tags: list[str] = field(default_factory=list)  # fintech, healthtech, ecommerce…

    @classmethod
    def create(cls, *, user_id: UUID, name: str, **kw: Any) -> Project:
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
    # evidence_refs dropped in migration 0017 — skill→evidence relations
    # live as :DEMONSTRATES edges in the AGE graph.

    @classmethod
    def create(cls, *, user_id: UUID, name: str, category: str = "hard", **kw: Any) -> Skill:
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
    def create(cls, *, user_id: UUID, name: str, **kw: Any) -> Certification:
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
    def create(cls, *, user_id: UUID, title: str, **kw: Any) -> Course:
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
    def create(cls, *, user_id: UUID, code: str, name: str, level: str, **kw: Any) -> Language:
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
    def create(cls, *, user_id: UUID, title: str, **kw: Any) -> Achievement:
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
    def create(cls, *, user_id: UUID, name: str, **kw: Any) -> Interest:
        from src.shared.errors import ValidationError

        if not name.strip():
            raise ValidationError("Interest name is required")
        return cls(id=uuid4(), user_id=user_id, name=name.strip(), **kw)

    def embedding_text(self) -> str:
        return self.name


# --- CareerPreferences (singleton per user) ------------------------------


# --- AreaStrength (one row per user × canonical area) --------------------


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

ShapeType = Literal["I", "T", "π", "M", "none"]


@dataclass
class AreaStrength:
    id: UUID
    user_id: UUID
    area: str
    depth_years: float = 0.0
    breadth_count: int = 0
    recency_months: int | None = None
    confidence: float = 0.0
    is_primary: bool = False
    computed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(cls, *, user_id: UUID, area: str, **kw: Any) -> AreaStrength:
        if area not in CANONICAL_AREAS:
            from src.shared.errors import ValidationError

            raise ValidationError(
                f"Invalid area {area!r}",
                details={"allowed": list(CANONICAL_AREAS)},
            )
        return cls(id=uuid4(), user_id=user_id, area=area, **kw)


# --- Artifact (GitHub repos, talks, blog posts, OSS, papers, podcasts, …) --


ArtifactType = Literal[
    "github_repo",
    "talk",
    "blog_post",
    "oss_contrib",
    "paper",
    "podcast",
    "video",
    "book",
    "other",
]

_ARTIFACT_TYPES = {
    "github_repo",
    "talk",
    "blog_post",
    "oss_contrib",
    "paper",
    "podcast",
    "video",
    "book",
    "other",
}


@dataclass
class Artifact(_Base):
    type: str = "other"
    title: str = ""
    url: str = ""
    year: int | None = None
    description: str | None = None
    venue: str | None = None
    # linked_skill_ids / linked_project_id dropped in migration 0017 —
    # artifact relations live as :USES_TECH / :PART_OF edges in the graph.
    metrics: dict[str, Any] | None = None

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        type: str,
        title: str,
        url: str,
        **kw: Any,
    ) -> Artifact:
        from src.shared.errors import ValidationError

        if type not in _ARTIFACT_TYPES:
            raise ValidationError(
                f"Invalid artifact type {type!r}",
                details={"allowed": sorted(_ARTIFACT_TYPES)},
            )
        if not title.strip():
            raise ValidationError("Artifact title is required")
        if not url.strip():
            raise ValidationError("Artifact url is required")
        return cls(
            id=uuid4(),
            user_id=user_id,
            type=type,
            title=title.strip(),
            url=url.strip(),
            **kw,
        )

    def embedding_text(self) -> str:
        return " — ".join(
            p for p in [self.type, self.title, self.description, self.venue] if p
        )


# --- SkillStack (nameable cluster of related skills) ---------------------


@dataclass
class SkillStack:
    id: UUID
    user_id: UUID
    name: str = ""
    slug: str = ""
    area: str = "other"
    skill_ids: list[UUID] = field(default_factory=list)
    description: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        name: str,
        slug: str,
        area: str,
        **kw: Any,
    ) -> SkillStack:
        from src.shared.errors import ValidationError

        if not name.strip():
            raise ValidationError("SkillStack name is required")
        if not slug.strip():
            raise ValidationError("SkillStack slug is required")
        if area not in CANONICAL_AREAS:
            raise ValidationError(
                f"Invalid area {area!r}",
                details={"allowed": list(CANONICAL_AREAS)},
            )
        return cls(
            id=uuid4(),
            user_id=user_id,
            name=name.strip(),
            slug=slug.strip(),
            area=area,
            **kw,
        )


# --- UserRubricSignal (overlay personal sobre rúbricas globales) -----------


SIGNAL_STATUSES = ("aspire", "practice", "own", "teach", "avoid")
SIGNAL_SECTION_KINDS = ("criteria", "questions", "signals", "anti_patterns", "resources", "general")


@dataclass
class UserRubricSignal:
    id: UUID
    user_id: UUID
    rubric_chunk_id: UUID
    section_kind: str = "signals"
    status: str = "aspire"
    confidence: float = 0.0
    evidence_entity_type: str | None = None
    evidence_entity_ids: list[UUID] = field(default_factory=list)
    notes: str | None = None
    source: str = "auto"
    last_reviewed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        rubric_chunk_id: UUID,
        section_kind: str,
        status: str,
        **kw: Any,
    ) -> UserRubricSignal:
        from src.shared.errors import ValidationError

        if status not in SIGNAL_STATUSES:
            raise ValidationError(
                f"Invalid signal status {status!r}",
                details={"allowed": list(SIGNAL_STATUSES)},
            )
        if section_kind not in SIGNAL_SECTION_KINDS:
            raise ValidationError(
                f"Invalid section_kind {section_kind!r}",
                details={"allowed": list(SIGNAL_SECTION_KINDS)},
            )
        return cls(
            id=uuid4(),
            user_id=user_id,
            rubric_chunk_id=rubric_chunk_id,
            section_kind=section_kind,
            status=status,
            **kw,
        )


# --- ArchitectureDecision (ADR) -----------------------------------------


ADR_STATUSES = ("proposed", "accepted", "superseded", "rejected")


@dataclass
class ArchitectureDecision(_Base):
    title: str = ""
    context: str | None = None
    decision: str | None = None
    consequences: str | None = None
    status: str = "proposed"
    tags: list[str] = field(default_factory=list)
    # superseded_by / related_project_id dropped in migration 0017 — ADR
    # relations live as :SUPERSEDES / :PART_OF edges in the graph.

    @classmethod
    def create(cls, *, user_id: UUID, title: str, **kw: Any) -> ArchitectureDecision:
        from src.shared.errors import ValidationError

        if not title.strip():
            raise ValidationError("ADR title is required")
        status = kw.get("status", "proposed")
        if status not in ADR_STATUSES:
            raise ValidationError(
                f"Invalid ADR status {status!r}",
                details={"allowed": list(ADR_STATUSES)},
            )
        return cls(id=uuid4(), user_id=user_id, title=title.strip(), **kw)

    def embedding_text(self) -> str:
        return " — ".join(
            p for p in [self.title, self.context, self.decision] if p
        )


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
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
