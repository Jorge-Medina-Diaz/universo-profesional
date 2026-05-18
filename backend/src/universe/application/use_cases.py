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


# --- CareerPreferences -----------------------------------------------------


class SetCareerPreferences:
    def __init__(self, repo: CareerPreferencesRepository) -> None:
        self._repo = repo

    async def execute(self, *, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        existing = await self._repo.get(UUID(user_id))
        from datetime import datetime as _dt

        if existing is None:
            existing = CareerPreferences(user_id=UUID(user_id))
        for k, v in patch.items():
            if hasattr(existing, k):
                setattr(existing, k, v)
        existing.updated_at = _dt.utcnow()
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
        from datetime import datetime as _dt

        uid = UUID(user_id)
        universe = await self._repo.get(uid)
        if universe is None:
            universe = Universe.for_user(uid)
        universe.update(
            headline=patch.get("headline", ...),
            summary=patch.get("summary", ...),
            photo_url=patch.get("photo_url", ...),
            current_status=patch.get("current_status", ...),
            now=_dt.utcnow(),
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
