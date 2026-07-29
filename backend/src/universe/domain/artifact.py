"""Artifact entity."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID, uuid4

from src.universe.domain.entities import _Base

ArtifactType = Literal[
    "github_repo",
    "talk",
    "blog_post",
    "oss_contrib",
    "paper",
    "podcast",
    "video",
    "book",
    "other",
]

_ARTIFACT_TYPES = {
    "github_repo",
    "talk",
    "blog_post",
    "oss_contrib",
    "paper",
    "podcast",
    "video",
    "book",
    "other",
}


@dataclass
class Artifact(_Base):
    type: str = "other"
    title: str = ""
    url: str = ""
    year: int | None = None
    description: str | None = None
    venue: str | None = None
    # linked_skill_ids / linked_project_id dropped in migration 0017 —
    # artifact relations live as :USES_TECH / :PART_OF edges in the graph.
    metrics: dict[str, Any] | None = None

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        type: str,
        title: str,
        url: str,
        **kw: Any,
    ) -> Artifact:
        from src.shared.errors import ValidationError

        if type not in _ARTIFACT_TYPES:
            raise ValidationError(
                f"Invalid artifact type {type!r}",
                details={"allowed": sorted(_ARTIFACT_TYPES)},
            )
        if not title.strip():
            raise ValidationError("Artifact title is required")
        if not url.strip():
            raise ValidationError("Artifact url is required")
        return cls(
            id=uuid4(),
            user_id=user_id,
            type=type,
            title=title.strip(),
            url=url.strip(),
            **kw,
        )

    def embedding_text(self) -> str:
        return " — ".join(
            p for p in [self.type, self.title, self.description, self.venue] if p
        )
