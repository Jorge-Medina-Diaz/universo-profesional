"""Notes REST API: /api/v1/notes/*"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.notes.application.use_cases import (
    CreateNote,
    DeleteNote,
    GetNote,
    ListNotes,
    UpdateNote,
)
from src.notes.infrastructure.repositories import SqlAlchemyNoteRepository
from src.shared.uow import unit_of_work
from src.universe.infrastructure.scheduler import ArqEmbeddingScheduler

router = APIRouter()


class NoteCreateBody(BaseModel):
    title: str | None = Field(None, max_length=200)
    body_md: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)


class NotePatchBody(BaseModel):
    title: str | None = None
    body_md: str | None = None
    tags: list[str] | None = None


def _scheduler() -> ArqEmbeddingScheduler:
    return ArqEmbeddingScheduler()


@router.get("")
async def list_notes(
    user_id: CurrentUserId,
    session: SessionDep,
    tag: list[str] | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    uc = ListNotes(SqlAlchemyNoteRepository(session))
    return await uc.execute(user_id=user_id, tags=tag, limit=limit)


@router.post("")
async def create_note(
    body: NoteCreateBody, user_id: CurrentUserId, session: SessionDep
) -> dict[str, Any]:
    uc = CreateNote(SqlAlchemyNoteRepository(session), _scheduler())
    async with unit_of_work(session) as uow:
        result = await uc.execute(user_id=user_id, payload=body.model_dump(), uow=uow)
        if result.is_failure:
            raise result.error
        await uow.commit()
        return result.value


@router.get("/{note_id}")
async def get_note(
    note_id: str, user_id: CurrentUserId, session: SessionDep
) -> dict[str, Any]:
    uc = GetNote(SqlAlchemyNoteRepository(session))
    result = await uc.execute(user_id=user_id, note_id=note_id)
    if result.is_failure:
        raise result.error
    return result.value


@router.patch("/{note_id}")
async def patch_note(
    note_id: str,
    body: NotePatchBody,
    user_id: CurrentUserId,
    session: SessionDep,
) -> dict[str, Any]:
    uc = UpdateNote(SqlAlchemyNoteRepository(session), _scheduler())
    async with unit_of_work(session) as uow:
        result = await uc.execute(
            user_id=user_id,
            note_id=note_id,
            patch={k: v for k, v in body.model_dump().items() if v is not None},
            uow=uow,
        )
        if result.is_failure:
            raise result.error
        await uow.commit()
        return result.value


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: str, user_id: CurrentUserId, session: SessionDep
) -> None:
    uc = DeleteNote(SqlAlchemyNoteRepository(session))
    async with unit_of_work(session) as uow:
        result = await uc.execute(user_id=user_id, note_id=note_id, uow=uow)
        if result.is_failure:
            raise result.error
        await uow.commit()
