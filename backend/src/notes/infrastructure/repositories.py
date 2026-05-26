"""SQLAlchemy repository for Notes."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.notes.domain.entities import Note
from src.notes.infrastructure.orm import NoteOrm


class SqlAlchemyNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        user_id: UUID,
        *,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[Note]:
        stmt = select(NoteOrm).where(NoteOrm.user_id == user_id, NoteOrm.deleted_at.is_(None))
        if tags:
            # ARRAY overlap operator — any of `tags` matches
            stmt = stmt.where(NoteOrm.tags.overlap(tags))
        stmt = stmt.order_by(NoteOrm.updated_at.desc()).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_orm_to_entity(r) for r in rows]

    async def get(self, user_id: UUID, note_id: UUID) -> Note | None:
        stmt = select(NoteOrm).where(NoteOrm.id == note_id, NoteOrm.user_id == user_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _orm_to_entity(row) if row else None

    async def add(self, note: Note) -> None:
        self._session.add(
            NoteOrm(
                id=note.id,
                user_id=note.user_id,
                title=note.title,
                body_md=note.body_md,
                tags=note.tags,
                source=note.source,
                source_metadata=note.source_metadata,
                confidence=note.confidence,
                visibility=note.visibility,
            )
        )
        await self._session.flush()

    async def update(self, note: Note) -> None:
        existing = await self._session.get(NoteOrm, note.id)
        if existing is None:
            return
        existing.title = note.title
        existing.body_md = note.body_md
        existing.tags = note.tags
        existing.source_metadata = note.source_metadata
        existing.confidence = note.confidence
        existing.visibility = note.visibility
        from src.shared.security import utc_now

        existing.updated_at = utc_now()
        await self._session.flush()

    async def soft_delete(self, user_id: UUID, note_id: UUID) -> bool:
        result = await self._session.execute(
            text(
                "UPDATE notes SET deleted_at = now() "
                "WHERE id = :id AND user_id = :uid AND deleted_at IS NULL "
                "RETURNING id"
            ),
            {"id": str(note_id), "uid": str(user_id)},
        )
        return result.first() is not None

    async def update_embedding(self, note_id: UUID, embedding: list[float]) -> None:
        await self._session.execute(
            text("UPDATE notes SET embedding = CAST(:emb AS vector) WHERE id = :id"),
            {"id": str(note_id), "emb": "[" + ",".join(f"{x:.7f}" for x in embedding) + "]"},
        )


def _orm_to_entity(o: NoteOrm) -> Note:
    return Note(
        id=o.id,
        user_id=o.user_id,
        title=o.title,
        body_md=o.body_md,
        tags=list(o.tags or []),
        source=o.source,
        source_metadata=o.source_metadata,
        confidence=o.confidence,
        visibility=o.visibility,
        created_at=o.created_at,
        updated_at=o.updated_at,
        last_reviewed_at=o.last_reviewed_at,
    )
