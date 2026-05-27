"""ArchitectureDecision entity."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from src.universe.domain.entities import _Base


ADR_STATUSES = ("proposed", "accepted", "superseded", "rejected")


@dataclass
class ArchitectureDecision(_Base):
    title: str = ""
    context: str | None = None
    decision: str | None = None
    consequences: str | None = None
    status: str = "proposed"
    tags: list[str] = field(default_factory=list)
    # superseded_by / related_project_id dropped in migration 0017 — ADR
    # relations live as :SUPERSEDES / :PART_OF edges in the graph.

    @classmethod
    def create(cls, *, user_id: UUID, title: str, **kw: Any) -> ArchitectureDecision:
        from src.shared.errors import ValidationError

        if not title.strip():
            raise ValidationError("ADR title is required")
        status = kw.get("status", "proposed")
        if status not in ADR_STATUSES:
            raise ValidationError(
                f"Invalid ADR status {status!r}",
                details={"allowed": list(ADR_STATUSES)},
            )
        return cls(id=uuid4(), user_id=user_id, title=title.strip(), **kw)

    def embedding_text(self) -> str:
        return " — ".join(
            p for p in [self.title, self.context, self.decision] if p
        )
