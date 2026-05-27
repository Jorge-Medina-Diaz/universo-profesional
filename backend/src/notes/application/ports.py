"""Application-layer ports for notes."""
from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.notes.domain.entities import Note


class NoteRepository(Protocol):
    async def list(
        self,
        user_id: UUID,
        *,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[Note]: ...

    async def get(self, user_id: UUID, note_id: UUID) -> Note | None: ...

    async def add(self, note: Note) -> None: ...

    async def update(self, note: Note) -> None: ...

    async def soft_delete(self, user_id: UUID, note_id: UUID) -> bool: ...


class EmbeddingRefreshScheduler(Protocol):
    async def enqueue(self, *, entity_type: str, entity_id: UUID) -> None: ...
