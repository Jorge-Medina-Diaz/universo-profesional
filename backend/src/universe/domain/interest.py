"""Interest entity."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from src.universe.domain.entities import _Base


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
