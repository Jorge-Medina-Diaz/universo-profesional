"""Achievement entity."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID, uuid4

from src.universe.domain.entities import _Base


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
