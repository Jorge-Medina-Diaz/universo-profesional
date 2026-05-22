"""Use cases for the Notes context.

Mirrors the structure of `universe/application/use_cases.py`: each operation
constructs the domain entity, persists via the repository, schedules an
embedding refresh, and emits a domain event.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, ClassVar
from uuid import UUID

from src.notes.domain.entities import Note
from src.notes.infrastructure.repositories import SqlAlchemyNoteRepository
from src.shared.errors import NotFoundError, ValidationError
from src.shared.events import DomainEvent
from src.shared.result import Result, err, ok
from src.shared.uow import UnitOfWork
from src.universe.infrastructure.scheduler import ArqEmbeddingScheduler


@dataclass(frozen=True, kw_only=True)
class NoteCreated(DomainEvent):
    note_id: UUID
    event_type: ClassVar[str] = "notes.created"


@dataclass(frozen=True, kw_only=True)
class NoteUpdated(DomainEvent):
    note_id: UUID
    event_type: ClassVar[str] = "notes.updated"


@dataclass(frozen=True, kw_only=True)
class NoteDeleted(DomainEvent):
    note_id: UUID
    event_type: ClassVar[str] = "notes.deleted"


def _serialize(note: Note) -> dict[str, Any]:
    from datetime import date, datetime
    from uuid import UUID as _UUID

    d = asdict(note)
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
        elif isinstance(v, date):
            d[k] = v.isoformat()
        elif isinstance(v, _UUID):
            d[k] = str(v)
    return d


class CreateNote:
    def __init__(
        self, repo: SqlAlchemyNoteRepository, scheduler: ArqEmbeddingScheduler
    ) -> None:
        self._repo = repo
        self._scheduler = scheduler

    async def execute(
        self,
        *,
        user_id: str,
        payload: dict[str, Any],
        uow: UnitOfWork,
    ) -> Result[dict[str, Any], ValidationError]:
        try:
            note = Note.create(user_id=UUID(user_id), **payload)
        except ValidationError as e:
            return err(e)
        await self._repo.add(note)
        await self._scheduler.enqueue(entity_type="note", entity_id=note.id)
        uow.add_event(NoteCreated(user_id=UUID(user_id), note_id=note.id))
        return ok(_serialize(note))


class UpdateNote:
    def __init__(
        self, repo: SqlAlchemyNoteRepository, scheduler: ArqEmbeddingScheduler
    ) -> None:
        self._repo = repo
        self._scheduler = scheduler

    async def execute(
        self,
        *,
        user_id: str,
        note_id: str,
        patch: dict[str, Any],
        uow: UnitOfWork,
    ) -> Result[dict[str, Any], NotFoundError | ValidationError]:
        note = await self._repo.get(UUID(user_id), UUID(note_id))
        if note is None:
            return err(NotFoundError("Note not found"))
        # Validate non-empty body if it's being replaced.
        if "body_md" in patch:
            new_body = (patch["body_md"] or "").strip()
            if not new_body:
                return err(ValidationError("Note body cannot be empty"))
            note.body_md = new_body
        if "title" in patch:
            note.title = (patch["title"] or "").strip() or None
        if "tags" in patch:
            note.tags = [t.strip().lower() for t in (patch["tags"] or []) if t.strip()]
        if "source_metadata" in patch:
            note.source_metadata = patch["source_metadata"]
        await self._repo.update(note)
        await self._scheduler.enqueue(entity_type="note", entity_id=note.id)
        uow.add_event(NoteUpdated(user_id=UUID(user_id), note_id=note.id))
        return ok(_serialize(note))


class ListNotes:
    def __init__(self, repo: SqlAlchemyNoteRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        *,
        user_id: str,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        items = await self._repo.list(UUID(user_id), tags=tags, limit=limit)
        return [_serialize(i) for i in items]


class GetNote:
    def __init__(self, repo: SqlAlchemyNoteRepository) -> None:
        self._repo = repo

    async def execute(
        self, *, user_id: str, note_id: str
    ) -> Result[dict[str, Any], NotFoundError]:
        note = await self._repo.get(UUID(user_id), UUID(note_id))
        if note is None:
            return err(NotFoundError("Note not found"))
        return ok(_serialize(note))


class DeleteNote:
    def __init__(self, repo: SqlAlchemyNoteRepository) -> None:
        self._repo = repo

    async def execute(
        self, *, user_id: str, note_id: str, uow: UnitOfWork
    ) -> Result[bool, NotFoundError]:
        deleted = await self._repo.soft_delete(UUID(user_id), UUID(note_id))
        if not deleted:
            return err(NotFoundError("Note not found"))
        uow.add_event(NoteDeleted(user_id=UUID(user_id), note_id=UUID(note_id)))
        return ok(True)
