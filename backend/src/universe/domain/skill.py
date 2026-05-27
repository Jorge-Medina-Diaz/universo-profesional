"""Skill entity."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from src.shared.value_objects import validate_skill_level
from src.universe.domain.entities import _Base


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
