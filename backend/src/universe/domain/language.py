"""Language entity."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from src.shared.value_objects import validate_cefr
from src.universe.domain.entities import _Base


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
