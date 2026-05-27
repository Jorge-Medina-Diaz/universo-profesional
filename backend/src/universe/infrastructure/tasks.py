"""Arq tasks for Universe (embedding refresh)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from src.shared.db import get_session_factory
from src.shared.embeddings import get_embeddings_service
from src.universe.domain.entities import (
    Achievement,
    ArchitectureDecision,
    Artifact,
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
    ArchitectureDecisionOrm,
    ArtifactOrm,
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
    # Sprint G — portfolio artifacts
    "artifact": (ArtifactOrm, Artifact),
    # Sprint K — architecture decision records
    "architecture_decision": (ArchitectureDecisionOrm, ArchitectureDecision),
}


def _is_note(entity_type: str) -> bool:
    return entity_type == "note"


async def refresh_embedding(ctx: dict[str, Any], *, entity_type: str, entity_id: str) -> None:
    embedder = get_embeddings_service()
    factory = get_session_factory()

    if _is_note(entity_type):
        from src.notes.infrastructure.orm import NoteOrm

        async with factory() as session:
            row = await session.get(NoteOrm, UUID(entity_id))
            if row is None:
                return
            parts = [p for p in [row.title, row.body_md, " ".join(row.tags or [])] if p]
            text = " — ".join(parts)
            vec = await embedder.embed(text)
            row.embedding = vec
            await session.commit()
            logger.debug("embedding_refreshed", entity_type=entity_type, entity_id=entity_id)
        return

    if entity_type not in _ENTITY_MAP:
        logger.warning("refresh_embedding_unknown_type", entity_type=entity_type)
        return
    orm_cls, entity_cls = _ENTITY_MAP[entity_type]

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


async def enrich_universe_task(ctx: dict[str, Any], *, user_id: str) -> dict[str, int]:
    """Background full-universe relationship enrichment for one user.

    Infers semantic (RELATED_TO) + structural (USES_TECH/PART_OF) edges across
    the user's entities and writes them via the graph layer. Idempotent.
    """
    from src.universe.application.enrichment import enrich_user_graph

    factory = get_session_factory()
    async with factory() as session:
        stats = await enrich_user_graph(session, UUID(user_id))
        await session.commit()
        logger.info("enrich_universe_task_done", user_id=user_id, **stats.as_dict())
        return stats.as_dict()


async def compute_communities_task(ctx: dict[str, Any], *, user_id: str) -> dict[str, int]:
    """Background community detection ("career pillars") for one user."""
    from src.graph.application.communities import compute_communities

    factory = get_session_factory()
    async with factory() as session:
        pillars = await compute_communities(session, UUID(user_id))
        await session.commit()
        logger.info("compute_communities_task_done", user_id=user_id, count=len(pillars))
        return {"communities": len(pillars)}


# ---------------------------------------------------------------------------
# Wire module-level ports so application layer stays import-clean.
# ---------------------------------------------------------------------------

from src.universe.application.ports import tasks as _tasks_port  # noqa: E402

_tasks_port.ENTITY_MAP = _ENTITY_MAP
_tasks_port.refresh_embedding = refresh_embedding
