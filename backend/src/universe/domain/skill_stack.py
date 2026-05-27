"""SkillStack entity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.universe.domain.entities import CANONICAL_AREAS


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
