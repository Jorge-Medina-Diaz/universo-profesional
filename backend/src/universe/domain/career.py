"""Career-related domain types."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from src.universe.domain.entities import CANONICAL_AREAS

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
