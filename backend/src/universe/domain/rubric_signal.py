"""UserRubricSignal entity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

SIGNAL_STATUSES = ("aspire", "practice", "own", "teach", "avoid")
SIGNAL_SECTION_KINDS = ("criteria", "questions", "signals", "anti_patterns", "resources", "general")


@dataclass
class UserRubricSignal:
    id: UUID
    user_id: UUID
    rubric_chunk_id: UUID
    section_kind: str = "signals"
    status: str = "aspire"
    confidence: float = 0.0
    evidence_entity_type: str | None = None
    evidence_entity_ids: list[UUID] = field(default_factory=list)
    notes: str | None = None
    source: str = "auto"
    last_reviewed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        rubric_chunk_id: UUID,
        section_kind: str,
        status: str,
        **kw: Any,
    ) -> UserRubricSignal:
        from src.shared.errors import ValidationError

        if status not in SIGNAL_STATUSES:
            raise ValidationError(
                f"Invalid signal status {status!r}",
                details={"allowed": list(SIGNAL_STATUSES)},
            )
        if section_kind not in SIGNAL_SECTION_KINDS:
            raise ValidationError(
                f"Invalid section_kind {section_kind!r}",
                details={"allowed": list(SIGNAL_SECTION_KINDS)},
            )
        return cls(
            id=uuid4(),
            user_id=user_id,
            rubric_chunk_id=rubric_chunk_id,
            section_kind=section_kind,
            status=status,
            **kw,
        )
