"""Project entity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import UUID, uuid4

from src.universe.domain.entities import _Base


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
