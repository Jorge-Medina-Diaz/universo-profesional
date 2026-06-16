"""Entity CRUD use cases — generic base + per-entity subclasses.

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
from src.shared.result import Result, err, ok
from src.shared.uow import UnitOfWork
from src.universe.application.ports import EmbeddingRefreshScheduler
from src.universe.domain.entities import (
    Achievement,
    ArchitectureDecision,
    Artifact,
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
    coerce_patch,
)


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


# --- Generic CRUD factory --------------------------------------------------


class _EntityCrud:
    """Composable CRUD used by every entity endpoint and MCP tool.

    Each subclass binds an entity class (``entity_cls``) + ``entity_type``
    literal. ``add``/``update`` are generic; subclasses override only for
    per-entity logic (uniqueness checks, non-``**payload`` constructors).
    ``enqueue_on_update = False`` skips the embedding refresh on edit for kinds
    that don't re-embed (language/achievement/interest/artifact).
    """

    entity_type: str = ""
    entity_cls: type[Any] = object
    enqueue_on_update: bool = True

    def __init__(
        self,
        repo: Any,
        scheduler: EmbeddingRefreshScheduler,
    ) -> None:
        self._repo = repo
        self._scheduler = scheduler

    def _apply_patch(self, item: Any, patch: dict[str, Any]) -> None:
        """Apply a patch to a domain entity, coercing each field to its declared
        type. JSON/import carries dates/numbers/uuids as strings, and asyncpg
        rejects a str where a date/int/uuid is expected (→ 500). This mirrors
        the create-time coercion in `_Base.__post_init__`, so UPDATE/merge is
        as type-safe as create. Invalid values raise ValidationError (→ 422)."""
        coerced = coerce_patch(type(item), patch)
        for k, v in coerced.items():
            if hasattr(item, k):
                setattr(item, k, v)

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

    async def add(
        self, *, user_id: str, payload: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], ValidationError]:
        try:
            entity = self.entity_cls.create(user_id=UUID(user_id), **payload)
        except ValidationError as e:
            return err(e)
        await self._repo.add(entity)
        await self._scheduler.enqueue(entity_type=self.entity_type, entity_id=entity.id)
        uow.add_event(
            EntryAdded(
                user_id=UUID(user_id),
                entity_type=self.entity_type,
                entity_id_str=str(entity.id),
            )
        )
        return ok(_serialize(entity))

    async def update(
        self, *, user_id: str, entity_id: str, patch: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], NotFoundError | ValidationError]:
        item = await self._repo.get(UUID(user_id), UUID(entity_id))
        if item is None:
            return err(NotFoundError(f"{self.entity_cls.__name__} not found"))
        self._apply_patch(item, patch)
        await self._repo.update(item)
        if self.enqueue_on_update:
            await self._scheduler.enqueue(entity_type=self.entity_type, entity_id=item.id)
        uow.add_event(
            EntryUpdated(
                user_id=UUID(user_id),
                entity_type=self.entity_type,
                entity_id_str=str(item.id),
            )
        )
        return ok(_serialize(item))


# --- Generic-add/update entities -------------------------------------------


class EducationCrud(_EntityCrud):
    entity_type = "education"
    entity_cls = Education


class ExperienceCrud(_EntityCrud):
    entity_type = "experience"
    entity_cls = Experience


class ProjectCrud(_EntityCrud):
    entity_type = "project"
    entity_cls = Project


class CertificationCrud(_EntityCrud):
    entity_type = "certification"
    entity_cls = Certification


class CourseCrud(_EntityCrud):
    entity_type = "course"
    entity_cls = Course


# These kinds don't re-embed on edit → skip the embedding-refresh enqueue.
class LanguageCrud(_EntityCrud):
    entity_type = "language"
    entity_cls = Language
    enqueue_on_update = False


class AchievementCrud(_EntityCrud):
    entity_type = "achievement"
    entity_cls = Achievement
    enqueue_on_update = False


class InterestCrud(_EntityCrud):
    entity_type = "interest"
    entity_cls = Interest
    enqueue_on_update = False


# --- Skills (uniqueness check on add) --------------------------------------


class SkillCrud(_EntityCrud):
    entity_type = "skill"
    entity_cls = Skill

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


# --- ArchitectureDecision (ADR) — non-**payload constructor ----------------


class ArchitectureDecisionCrud(_EntityCrud):
    entity_type = "architecture_decision"
    entity_cls = ArchitectureDecision

    async def add(
        self, *, user_id: str, payload: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], ValidationError]:
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


# --- Artifacts (non-**payload constructor; no embedding refresh) -----------


class ArtifactCrud(_EntityCrud):
    entity_type = "artifact"
    entity_cls = Artifact
    enqueue_on_update = False

    async def add(
        self, *, user_id: str, payload: dict[str, Any], uow: UnitOfWork
    ) -> Result[dict[str, Any], ValidationError]:
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
