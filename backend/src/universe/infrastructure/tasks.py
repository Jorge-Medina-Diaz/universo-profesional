"""Arq tasks for Universe (embedding refresh)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from src.shared.db import get_session_factory
from src.shared.embeddings import get_embeddings_service
from src.universe.domain.entities import (
    Achievement,
    Certification,
    Course,
    Education,
    Experience,
    Interest,
    Language,
    Project,
    Skill,
)
from src.universe.infrastructure.orm import (
    AchievementOrm,
    CertificationOrm,
    CourseOrm,
    EducationOrm,
    ExperienceOrm,
    InterestOrm,
    LanguageOrm,
    ProjectOrm,
    SkillOrm,
)

logger = structlog.get_logger(__name__)

_ENTITY_MAP: dict[str, tuple[Any, Any]] = {
    "education": (EducationOrm, Education),
    "experience": (ExperienceOrm, Experience),
    "project": (ProjectOrm, Project),
    "skill": (SkillOrm, Skill),
    "certification": (CertificationOrm, Certification),
    "course": (CourseOrm, Course),
    "language": (LanguageOrm, Language),
    "achievement": (AchievementOrm, Achievement),
    "interest": (InterestOrm, Interest),
}


async def refresh_embedding(ctx: dict[str, Any], *, entity_type: str, entity_id: str) -> None:
    if entity_type not in _ENTITY_MAP:
        logger.warning("refresh_embedding_unknown_type", entity_type=entity_type)
        return
    orm_cls, entity_cls = _ENTITY_MAP[entity_type]
    embedder = get_embeddings_service()

    factory = get_session_factory()
    async with factory() as session:
        row = await session.get(orm_cls, UUID(entity_id))
        if row is None:
            return
        # Build domain entity (only to get embedding_text); ignore embedding column
        fields = {f for f in entity_cls.__dataclass_fields__ if not f.startswith("_")}
        kwargs = {f: getattr(row, f) for f in fields if hasattr(row, f)}
        entity = entity_cls(**kwargs)
        text = entity.embedding_text() if hasattr(entity, "embedding_text") else str(entity)
        vec = await embedder.embed(text)
        row.embedding = vec
        await session.commit()
        logger.debug("embedding_refreshed", entity_type=entity_type, entity_id=entity_id)
