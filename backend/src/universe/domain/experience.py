"""Experience entity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import UUID, uuid4

from src.universe.domain.entities import _Base


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
