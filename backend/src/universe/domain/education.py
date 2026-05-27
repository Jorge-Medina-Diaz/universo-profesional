"""Education entity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import UUID, uuid4

from src.universe.domain.entities import _Base


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
