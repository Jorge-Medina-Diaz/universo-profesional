"""Note aggregate — markdown narrative + tags + soft links to universe."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from src.agents.domain.sources import SOURCE_AGENT_CHAT
from src.shared.errors import ValidationError


@dataclass
class Note:
    id: UUID
    user_id: UUID
    body_md: str
    title: str | None = None
    tags: list[str] = field(default_factory=list)
    source: str = SOURCE_AGENT_CHAT
    source_metadata: dict[str, Any] | None = None
    confidence: float = 1.0
    visibility: str = "private"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_reviewed_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        body_md: str,
        title: str | None = None,
        tags: list[str] | None = None,
        source: str = SOURCE_AGENT_CHAT,
        source_metadata: dict[str, Any] | None = None,
    ) -> Note:
        if not (body_md or "").strip():
            raise ValidationError("Note body cannot be empty")
        cleaned_tags = [t.strip().lower() for t in (tags or []) if t.strip()]
        return cls(
            id=uuid4(),
            user_id=user_id,
            body_md=body_md.strip(),
            title=(title or "").strip() or None,
            tags=cleaned_tags,
            source=source,
            source_metadata=source_metadata,
        )

    def embedding_text(self) -> str:
        parts: list[str] = []
        if self.title:
            parts.append(self.title)
        parts.append(self.body_md)
        if self.tags:
            parts.append(" ".join(self.tags))
        return " — ".join(p for p in parts if p)
