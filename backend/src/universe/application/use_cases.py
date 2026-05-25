"""Universe use cases — CRUD per entity + summary + search.

Each mutating use case:
  1. validates input through the domain entity constructor (raises ValidationError)
  2. persists via the repository
  3. enqueues an embedding refresh task (best-effort, idempotent)
  4. emits a domain event consumed by subscribers (audit, embedding sync, etc.)
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import UUID

from src.shared.errors import ConflictError, NotFoundError, ValidationError
from src.shared.result import Failure, Result, Success, err, ok
from src.shared.uow import UnitOfWork
from src.universe.application.ports import (
    AchievementRepository,
    CareerPreferencesRepository,
    CertificationRepository,
    CourseRepository,
    EducationRepository,
    EmbeddingRefreshScheduler,
    ExperienceRepository,
    InterestRepository,
    LanguageRepository,
    ProjectRepository,
    SemanticSearchPort,
    SkillRepository,
    UniverseRepository,
)
from src.universe.domain.entities import (
    Achievement,
    ArchitectureDecision,
    CareerPreferences,
    Certification,
    Course,
    Education,
    EntryAdded,
    EntryRemoved,
    EntryUpdated,
    Experience,
    Interest,
    Language,
    Project,
    Skill,
)
from src.universe.domain.universe import Universe


def _serialize(entity: Any) -> dict[str, Any]:
    """Serialize a dataclass entity to a plain JSON-able dict (drop _events)."""
    d = asdict(entity)
    d.pop("_events", None)
    # UUID + date/datetime → str
    for k, v in list(d.items()):
        d[k] = _coerce(v)
    return d


def _coerce(v: Any) -> Any:
    from datetime import date, datetime
    from uuid import UUID

    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, list):
        return [_coerce(x) for x in v]
    if isinstance(v, dict):
        return {k: _coerce(val) for k, val in v.items()}
    return v


# --- Universe summary ------------------------------------------------------


class GetUniverseSummary:
    def __init__(
        self,
        universes: UniverseRepository,
        educations: EducationRepository,
        experiences: ExperienceRepository,
        skills: SkillRepository,
        languages: LanguageRepository,
        projects: ProjectRepository,
        prefs: CareerPreferencesRepository,
    ) -> None:
        self._universes = universes
        self._edu = educations
        self._exp = experiences
        self._skills = skills
        self._lang = languages
        self._proj = projects
        self._prefs = prefs

    async def execute(self, *, user_id: str) -> dict[str, Any]:
        uid = UUID(user_id)
        universe = await self._universes.get(uid)
        if universe is None:
            universe = Universe.for_user(uid)
            await self._universes.save(universe)
        edu = await self._edu.list(uid)
        exp = await self._exp.list(uid)
        skills = await self._skills.list(uid)
        langs = await self._lang.list(uid)
        projs = await self._proj.list(uid)
        prefs = await self._prefs.get(uid)
        return {
            "headline": universe.headline,
            "summary": universe.summary,
            "photo_url": universe.photo_url,
            "current_status": universe.current_status,
            "counts": {
                "educations": len(edu),
                "experiences": len(exp),
                "projects": len(projs),
                "skills": len(skills),
                "languages": len(langs),
            },
            "top_skills": [_serialize(s) for s in skills[:8]],
            "recent_experiences": [_serialize(e) for e in exp[:3]],
            "languages": [_serialize(lang) for lang in langs],
            "preferences": _serialize(prefs) if prefs else None,
        }


# --- Generic CRUD factory --------------------------------------------------


class _EntityCrud:
    """Composable CRUD used by every entity endpoint and MCP tool.

    Each subclass binds: entity class + repository + entity_type literal.
    """

    entity_type: str = ""

    def __init__(
        self,
        repo: Any,
        scheduler: EmbeddingRefreshScheduler,
    ) -> None:
        self._repo = repo
        self._scheduler = scheduler

    async def list(self, *, user_id: str) -> list[dict[str, Any]]:
        items = await self._repo.list(UUID(user_id))
        return [_serialize(i) for i in items]

    async def get(
        self, *, user_id: str, entity_id: str
    ) -> Result[dict[str, Any], NotFoundError]:
        item = await self._repo.get(UUID(user_id), UUID(entity_id))
        if item is None:
            return err(NotFoundError(f"{self.entity_type} not found"))
        return ok(_serialize(item))

    async def delete(
        self, *, user_id: str, entity_id: str, uow: UnitOfWork
    ) -> Result[bool, NotFoundError]:
        deleted = await self._repo.delete(UUID(user_id), UUID(entity_id))
        if not deleted:
            return err(NotFoundError(f"{self.entity_type} not found"))
        uow.add_event(
            EntryRemoved(
                user_id=UUID(user_id),
                entity_type=self.entity_type,
                entity_id_str=entity_id,
            )
        )
        return ok(True)


# --- Educations ------------------------------------------------------------


class EducationCrud(_EntityCrud):
    entity_type = "education"

    async def add(
        self, *, user_id: str, payload: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], ValidationError]:
        try:
            entity = Education.create(user_id=UUID(user_id), **payload)
        except ValidationError as e:
            return err(e)
        await self._repo.add(entity)
        await self._scheduler.enqueue(entity_type="education", entity_id=entity.id)
        uow.add_event(
            EntryAdded(
                user_id=UUID(user_id),
                entity_type="education",
                entity_id_str=str(entity.id),
            )
        )
        return ok(_serialize(entity))

    async def update(
        self,
        *,
        user_id: str,
        entity_id: str,
        patch: dict[str, Any],
        uow: UnitOfWork,
    ) -> Result[dict[str, Any], NotFoundError | ValidationError]:
        item = await self._repo.get(UUID(user_id), UUID(entity_id))
        if item is None:
            return err(NotFoundError("Education not found"))
        for k, v in patch.items():
            if hasattr(item, k):
                setattr(item, k, v)
        await self._repo.update(item)
        await self._scheduler.enqueue(entity_type="education", entity_id=item.id)
        uow.add_event(
            EntryUpdated(
                user_id=UUID(user_id),
                entity_type="education",
                entity_id_str=str(item.id),
            )
        )
        return ok(_serialize(item))


# --- Experiences -----------------------------------------------------------


class ExperienceCrud(_EntityCrud):
    entity_type = "experience"

    async def add(
        self, *, user_id: str, payload: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], ValidationError]:
        try:
            entity = Experience.create(user_id=UUID(user_id), **payload)
        except ValidationError as e:
            return err(e)
        await self._repo.add(entity)
        await self._scheduler.enqueue(entity_type="experience", entity_id=entity.id)
        uow.add_event(
            EntryAdded(
                user_id=UUID(user_id),
                entity_type="experience",
                entity_id_str=str(entity.id),
            )
        )
        return ok(_serialize(entity))

    async def update(
        self, *, user_id: str, entity_id: str, patch: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], NotFoundError | ValidationError]:
        item = await self._repo.get(UUID(user_id), UUID(entity_id))
        if item is None:
            return err(NotFoundError("Experience not found"))
        for k, v in patch.items():
            if hasattr(item, k):
                setattr(item, k, v)
        await self._repo.update(item)
        await self._scheduler.enqueue(entity_type="experience", entity_id=item.id)
        uow.add_event(
            EntryUpdated(
                user_id=UUID(user_id),
                entity_type="experience",
                entity_id_str=str(item.id),
            )
        )
        return ok(_serialize(item))


# --- Projects --------------------------------------------------------------


class ProjectCrud(_EntityCrud):
    entity_type = "project"

    async def add(
        self, *, user_id: str, payload: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], ValidationError]:
        try:
            entity = Project.create(user_id=UUID(user_id), **payload)
        except ValidationError as e:
            return err(e)
        await self._repo.add(entity)
        await self._scheduler.enqueue(entity_type="project", entity_id=entity.id)
        uow.add_event(
            EntryAdded(
                user_id=UUID(user_id),
                entity_type="project",
                entity_id_str=str(entity.id),
            )
        )
        return ok(_serialize(entity))

    async def update(
        self, *, user_id: str, entity_id: str, patch: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], NotFoundError | ValidationError]:
        item = await self._repo.get(UUID(user_id), UUID(entity_id))
        if item is None:
            return err(NotFoundError("Project not found"))
        for k, v in patch.items():
            if hasattr(item, k):
                setattr(item, k, v)
        await self._repo.update(item)
        await self._scheduler.enqueue(entity_type="project", entity_id=item.id)
        uow.add_event(
            EntryUpdated(
                user_id=UUID(user_id),
                entity_type="project",
                entity_id_str=str(item.id),
            )
        )
        return ok(_serialize(item))


# --- Skills ----------------------------------------------------------------


class SkillCrud(_EntityCrud):
    entity_type = "skill"

    async def add(
        self, *, user_id: str, payload: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], ValidationError | ConflictError]:
        try:
            entity = Skill.create(user_id=UUID(user_id), **payload)
        except ValidationError as e:
            return err(e)
        existing = await self._repo.find_by_name(UUID(user_id), entity.name)
        if existing is not None:
            return err(ConflictError(f"Skill '{entity.name}' already exists"))
        await self._repo.add(entity)
        await self._scheduler.enqueue(entity_type="skill", entity_id=entity.id)
        uow.add_event(
            EntryAdded(
                user_id=UUID(user_id),
                entity_type="skill",
                entity_id_str=str(entity.id),
            )
        )
        return ok(_serialize(entity))

    async def update(
        self, *, user_id: str, entity_id: str, patch: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], NotFoundError | ValidationError]:
        item = await self._repo.get(UUID(user_id), UUID(entity_id))
        if item is None:
            return err(NotFoundError("Skill not found"))
        for k, v in patch.items():
            if hasattr(item, k):
                setattr(item, k, v)
        await self._repo.update(item)
        await self._scheduler.enqueue(entity_type="skill", entity_id=item.id)
        uow.add_event(
            EntryUpdated(
                user_id=UUID(user_id),
                entity_type="skill",
                entity_id_str=str(item.id),
            )
        )
        return ok(_serialize(item))


# --- Cert / Course / Language / Achievement / Interest ---------------------


class CertificationCrud(_EntityCrud):
    entity_type = "certification"

    async def add(
        self, *, user_id: str, payload: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], ValidationError]:
        try:
            entity = Certification.create(user_id=UUID(user_id), **payload)
        except ValidationError as e:
            return err(e)
        await self._repo.add(entity)
        await self._scheduler.enqueue(entity_type="certification", entity_id=entity.id)
        uow.add_event(
            EntryAdded(
                user_id=UUID(user_id),
                entity_type="certification",
                entity_id_str=str(entity.id),
            )
        )
        return ok(_serialize(entity))

    async def update(
        self, *, user_id: str, entity_id: str, patch: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], NotFoundError | ValidationError]:
        item = await self._repo.get(UUID(user_id), UUID(entity_id))
        if item is None:
            return err(NotFoundError("Certification not found"))
        for k, v in patch.items():
            if hasattr(item, k):
                setattr(item, k, v)
        await self._repo.update(item)
        await self._scheduler.enqueue(entity_type="certification", entity_id=item.id)
        uow.add_event(
            EntryUpdated(
                user_id=UUID(user_id),
                entity_type="certification",
                entity_id_str=str(item.id),
            )
        )
        return ok(_serialize(item))


class CourseCrud(_EntityCrud):
    entity_type = "course"

    async def add(
        self, *, user_id: str, payload: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], ValidationError]:
        try:
            entity = Course.create(user_id=UUID(user_id), **payload)
        except ValidationError as e:
            return err(e)
        await self._repo.add(entity)
        await self._scheduler.enqueue(entity_type="course", entity_id=entity.id)
        uow.add_event(
            EntryAdded(
                user_id=UUID(user_id),
                entity_type="course",
                entity_id_str=str(entity.id),
            )
        )
        return ok(_serialize(entity))

    async def update(
        self, *, user_id: str, entity_id: str, patch: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], NotFoundError | ValidationError]:
        item = await self._repo.get(UUID(user_id), UUID(entity_id))
        if item is None:
            return err(NotFoundError("Course not found"))
        for k, v in patch.items():
            if hasattr(item, k):
                setattr(item, k, v)
        await self._repo.update(item)
        uow.add_event(
            EntryUpdated(
                user_id=UUID(user_id),
                entity_type="course",
                entity_id_str=str(item.id),
            )
        )
        return ok(_serialize(item))


class LanguageCrud(_EntityCrud):
    entity_type = "language"

    async def add(
        self, *, user_id: str, payload: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], ValidationError]:
        try:
            entity = Language.create(user_id=UUID(user_id), **payload)
        except ValidationError as e:
            return err(e)
        await self._repo.add(entity)
        await self._scheduler.enqueue(entity_type="language", entity_id=entity.id)
        uow.add_event(
            EntryAdded(
                user_id=UUID(user_id),
                entity_type="language",
                entity_id_str=str(entity.id),
            )
        )
        return ok(_serialize(entity))

    async def update(
        self, *, user_id: str, entity_id: str, patch: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], NotFoundError | ValidationError]:
        item = await self._repo.get(UUID(user_id), UUID(entity_id))
        if item is None:
            return err(NotFoundError("Language not found"))
        for k, v in patch.items():
            if hasattr(item, k):
                setattr(item, k, v)
        await self._repo.update(item)
        uow.add_event(
            EntryUpdated(
                user_id=UUID(user_id),
                entity_type="language",
                entity_id_str=str(item.id),
            )
        )
        return ok(_serialize(item))


class AchievementCrud(_EntityCrud):
    entity_type = "achievement"

    async def add(
        self, *, user_id: str, payload: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], ValidationError]:
        try:
            entity = Achievement.create(user_id=UUID(user_id), **payload)
        except ValidationError as e:
            return err(e)
        await self._repo.add(entity)
        await self._scheduler.enqueue(entity_type="achievement", entity_id=entity.id)
        uow.add_event(
            EntryAdded(
                user_id=UUID(user_id),
                entity_type="achievement",
                entity_id_str=str(entity.id),
            )
        )
        return ok(_serialize(entity))

    async def update(
        self, *, user_id: str, entity_id: str, patch: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], NotFoundError | ValidationError]:
        item = await self._repo.get(UUID(user_id), UUID(entity_id))
        if item is None:
            return err(NotFoundError("Achievement not found"))
        for k, v in patch.items():
            if hasattr(item, k):
                setattr(item, k, v)
        await self._repo.update(item)
        uow.add_event(
            EntryUpdated(
                user_id=UUID(user_id),
                entity_type="achievement",
                entity_id_str=str(item.id),
            )
        )
        return ok(_serialize(item))


class InterestCrud(_EntityCrud):
    entity_type = "interest"

    async def add(
        self, *, user_id: str, payload: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], ValidationError]:
        try:
            entity = Interest.create(user_id=UUID(user_id), **payload)
        except ValidationError as e:
            return err(e)
        await self._repo.add(entity)
        await self._scheduler.enqueue(entity_type="interest", entity_id=entity.id)
        uow.add_event(
            EntryAdded(
                user_id=UUID(user_id),
                entity_type="interest",
                entity_id_str=str(entity.id),
            )
        )
        return ok(_serialize(entity))

    async def update(
        self, *, user_id: str, entity_id: str, patch: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], NotFoundError | ValidationError]:
        item = await self._repo.get(UUID(user_id), UUID(entity_id))
        if item is None:
            return err(NotFoundError("Interest not found"))
        for k, v in patch.items():
            if hasattr(item, k):
                setattr(item, k, v)
        await self._repo.update(item)
        uow.add_event(
            EntryUpdated(
                user_id=UUID(user_id),
                entity_type="interest",
                entity_id_str=str(item.id),
            )
        )
        return ok(_serialize(item))


# --- ArchitectureDecision (ADR) -----------------------------------------


class ArchitectureDecisionCrud(_EntityCrud):
    entity_type = "architecture_decision"

    async def add(
        self, *, user_id: str, payload: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], ValidationError]:
        from src.universe.domain.entities import ArchitectureDecision

        # related_project_id / superseded_by are no longer ADR columns
        # (migration 0017) — they flow to the graph as edges via the
        # coherence engine, so we don't pass them to the entity here.
        try:
            entity = ArchitectureDecision.create(
                user_id=UUID(user_id),
                title=payload.get("title", ""),
                context=payload.get("context"),
                decision=payload.get("decision"),
                consequences=payload.get("consequences"),
                status=payload.get("status", "proposed"),
                tags=payload.get("tags") or [],
                source=payload.get("source", "manual"),
            )
        except ValidationError as e:
            return err(e)
        await self._repo.add(entity)
        await self._scheduler.enqueue(
            entity_type="architecture_decision", entity_id=entity.id
        )
        uow.add_event(
            EntryAdded(
                user_id=UUID(user_id),
                entity_type="architecture_decision",
                entity_id_str=str(entity.id),
            )
        )
        return ok(_serialize(entity))

    async def update(
        self, *, user_id: str, entity_id: str, patch: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], NotFoundError | ValidationError]:
        item = await self._repo.get(UUID(user_id), UUID(entity_id))
        if item is None:
            return err(NotFoundError("ArchitectureDecision not found"))
        for k, v in patch.items():
            if hasattr(item, k):
                setattr(item, k, v)
        await self._repo.update(item)
        await self._scheduler.enqueue(
            entity_type="architecture_decision", entity_id=item.id
        )
        uow.add_event(
            EntryUpdated(
                user_id=UUID(user_id),
                entity_type="architecture_decision",
                entity_id_str=str(item.id),
            )
        )
        return ok(_serialize(item))


# --- Artifacts (portfolio first-class citizens) --------------------------


class ArtifactCrud(_EntityCrud):
    entity_type = "artifact"

    async def add(
        self, *, user_id: str, payload: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], ValidationError]:
        from src.universe.domain.entities import Artifact

        # linked_skill_ids / linked_project_id are no longer artifact
        # columns (migration 0017) — they flow to the graph as :USES_TECH
        # / :PART_OF edges via the coherence engine, not the entity here.
        try:
            entity = Artifact.create(
                user_id=UUID(user_id),
                type=payload.get("type", "other"),
                title=payload.get("title", ""),
                url=payload.get("url", ""),
                year=payload.get("year"),
                description=payload.get("description"),
                venue=payload.get("venue"),
                metrics=payload.get("metrics"),
                source=payload.get("source", "manual"),
            )
        except ValidationError as e:
            return err(e)
        await self._repo.add(entity)
        uow.add_event(
            EntryAdded(
                user_id=UUID(user_id),
                entity_type="artifact",
                entity_id_str=str(entity.id),
            )
        )
        return ok(_serialize(entity))

    async def update(
        self, *, user_id: str, entity_id: str, patch: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], NotFoundError | ValidationError]:
        item = await self._repo.get(UUID(user_id), UUID(entity_id))
        if item is None:
            return err(NotFoundError("Artifact not found"))
        for k, v in patch.items():
            if hasattr(item, k):
                setattr(item, k, v)
        await self._repo.update(item)
        uow.add_event(
            EntryUpdated(
                user_id=UUID(user_id),
                entity_type="artifact",
                entity_id_str=str(item.id),
            )
        )
        return ok(_serialize(item))


# --- CareerPreferences -----------------------------------------------------


class SetCareerPreferences:
    def __init__(self, repo: CareerPreferencesRepository) -> None:
        self._repo = repo

    async def execute(self, *, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        existing = await self._repo.get(UUID(user_id))
        from datetime import UTC as _UTC, datetime as _dt

        if existing is None:
            existing = CareerPreferences(user_id=UUID(user_id))
        for k, v in patch.items():
            if hasattr(existing, k):
                setattr(existing, k, v)
        existing.updated_at = _dt.now(_UTC)
        await self._repo.upsert(existing)
        return _serialize(existing)


class GetCareerPreferences:
    def __init__(self, repo: CareerPreferencesRepository) -> None:
        self._repo = repo

    async def execute(self, *, user_id: str) -> dict[str, Any] | None:
        existing = await self._repo.get(UUID(user_id))
        return _serialize(existing) if existing else None


# --- Universe-level update -------------------------------------------------


class UpdateUniverseHeader:
    def __init__(self, repo: UniverseRepository) -> None:
        self._repo = repo

    async def execute(
        self, *, user_id: str, patch: dict[str, Any], uow: UnitOfWork
    ) -> dict[str, Any]:
        from datetime import UTC as _UTC, datetime as _dt

        uid = UUID(user_id)
        universe = await self._repo.get(uid)
        if universe is None:
            universe = Universe.for_user(uid)
        universe.update(
            headline=patch.get("headline", ...),
            summary=patch.get("summary", ...),
            photo_url=patch.get("photo_url", ...),
            current_status=patch.get("current_status", ...),
            now=_dt.now(_UTC),
        )
        await self._repo.save(universe)
        uow.add_events(universe.pop_events())
        return {
            "user_id": str(universe.user_id),
            "headline": universe.headline,
            "summary": universe.summary,
            "photo_url": universe.photo_url,
            "current_status": universe.current_status,
        }


# --- Semantic search -------------------------------------------------------


class SearchUniverse:
    def __init__(
        self,
        search: SemanticSearchPort,
        embedder: Any,  # EmbeddingsProvider
    ) -> None:
        self._search = search
        self._embed = embedder

    async def execute(
        self, *, user_id: str, query: str, top_k: int = 10, entity_types: list[str] | None = None
    ) -> list[dict[str, Any]]:
        vec = await self._embed.embed(query)
        return await self._search.search(
            user_id=UUID(user_id),
            embedding=vec,
            top_k=top_k,
            entity_types=entity_types,
        )


# --- MarkReviewed -----------------------------------------------------------


class MarkReviewed:
    """Touch `last_reviewed_at` on an entity. Confirms the user has inspected it recently."""

    _TABLE_BY_TYPE = {
        "education": "educations",
        "experience": "experiences",
        "project": "projects",
        "skill": "skills",
        "certification": "certifications",
        "course": "courses",
        "language": "languages",
        "achievement": "achievements",
        "interest": "interests",
        # Sprint G/K
        "artifact": "artifacts",
        "architecture_decision": "architecture_decisions",
    }

    def __init__(self, session: Any) -> None:
        self._session = session

    async def execute(
        self, *, user_id: str, entity_type: str, entity_id: str
    ) -> Result[dict[str, str], NotFoundError | ValidationError]:
        from sqlalchemy import text

        table = self._TABLE_BY_TYPE.get(entity_type)
        if table is None:
            return err(ValidationError(f"Unknown entity_type {entity_type!r}"))
        stmt = text(
            f"UPDATE {table} SET last_reviewed_at = now() "  # noqa: S608
            f"WHERE id = :eid AND user_id = :uid RETURNING id"
        )
        result = await self._session.execute(
            stmt, {"eid": entity_id, "uid": user_id}
        )
        row = result.first()
        if row is None:
            return err(NotFoundError(f"{entity_type} not found"))
        return ok({"entity_type": entity_type, "entity_id": entity_id, "reviewed_at": "now"})


# --- GetActivity ------------------------------------------------------------


class GetActivity:
    """Read from domain_events table (populated by activity_log subscriber)."""

    def __init__(self, session: Any) -> None:
        self._session = session

    async def execute(
        self,
        *,
        user_id: str,
        limit: int = 50,
        since: str | None = None,
        event_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        from sqlalchemy import text

        params: dict[str, Any] = {"uid": user_id, "limit": limit}
        where = ["user_id = :uid"]
        if since:
            where.append("occurred_at >= :since")
            params["since"] = since
        if event_types:
            placeholders = ",".join(f":et{i}" for i in range(len(event_types)))
            where.append(f"event_type IN ({placeholders})")
            for i, et in enumerate(event_types):
                params[f"et{i}"] = et
        stmt = text(
            "SELECT event_id::text, event_type, occurred_at, payload "
            "FROM domain_events "
            f"WHERE {' AND '.join(where)} "
            "ORDER BY occurred_at DESC LIMIT :limit"
        )
        rows = await self._session.execute(stmt, params)
        return [
            {
                "event_id": r[0],
                "event_type": r[1],
                "occurred_at": r[2].isoformat() if r[2] else None,
                "payload": r[3],
            }
            for r in rows.fetchall()
        ]


# --- Evidence linking -------------------------------------------------------


class LinkEvidence:
    """Create a skill ↔ entity evidence link with weight."""

    def __init__(self, session: Any) -> None:
        self._session = session

    async def execute(
        self,
        *,
        user_id: str,
        skill_id: str,
        evidence_entity_type: str,
        evidence_entity_id: str,
        weight: float = 1.0,
        notes: str | None = None,
    ) -> Result[dict[str, Any], ValidationError]:
        from uuid import uuid4

        from src.shared.security import utc_now
        from src.universe.infrastructure.orm import EvidenceOrm

        if evidence_entity_type not in {"experience", "project", "achievement", "certification", "course"}:
            return err(ValidationError(f"Unknown evidence type {evidence_entity_type!r}"))
        ev = EvidenceOrm(
            id=uuid4(),
            user_id=UUID(user_id),
            skill_id=UUID(skill_id),
            evidence_entity_type=evidence_entity_type,
            evidence_entity_id=UUID(evidence_entity_id),
            weight=weight,
            notes=notes,
            created_at=utc_now(),
        )
        self._session.add(ev)
        await self._session.flush()
        return ok({"id": str(ev.id)})


class ListEvidence:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def execute(self, *, user_id: str, skill_id: str | None = None) -> list[dict[str, Any]]:
        from sqlalchemy import desc as sa_desc, select

        from src.universe.infrastructure.orm import EvidenceOrm

        stmt = (
            select(EvidenceOrm)
            .where(EvidenceOrm.user_id == UUID(user_id))
            .order_by(sa_desc(EvidenceOrm.created_at))
        )
        if skill_id:
            stmt = stmt.where(EvidenceOrm.skill_id == UUID(skill_id))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "id": str(r.id),
                "skill_id": str(r.skill_id),
                "evidence_entity_type": r.evidence_entity_type,
                "evidence_entity_id": str(r.evidence_entity_id),
                "weight": r.weight,
                "notes": r.notes,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
