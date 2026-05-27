"""Tools for the narrative `notes` layer.

The agent uses these when the user shares something that isn't a discrete
universe entity: ongoing learning, opinions, gustos, projects-in-progress
narratives. Notes can be tagged and later searched semantically.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from agno.run.base import RunContext
from agno.tools import tool

from src.agents.tools._deps import require_user_id
from src.notes.application.use_cases import (
    CreateNote,
    ListNotes,
    UpdateNote,
)
from src.notes.infrastructure.repositories import SqlAlchemyNoteRepository
from src.shared.db import with_user_session
from src.shared.uow import UnitOfWork
from src.universe.infrastructure.scheduler import ArqEmbeddingScheduler


@require_user_id
@tool(
    name="add_note",
    description=(
        "Create a freeform markdown note. Use for narrative biographical bits: "
        "learning threads, opinions, ongoing context. Tag liberally."
    ),
)
async def add_note(
    run_context: RunContext,
    body_md: str,
    title: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    user_id = run_context.user_id
    async with with_user_session(UUID(user_id)) as session:
        uc = CreateNote(SqlAlchemyNoteRepository(session), ArqEmbeddingScheduler())
        uow = UnitOfWork(session)
        result = await uc.execute(
            user_id=user_id,
            payload={"body_md": body_md, "title": title, "tags": tags or []},
            uow=uow,
        )
        if result.is_failure:
            await uow.rollback()
            return {"ok": False, "error": str(result.error)}
        await uow.commit()
        return {"ok": True, "note": result.value}


@require_user_id
@tool(
    name="update_note",
    description="Patch a note (title / body_md / tags).",
)
async def update_note(
    run_context: RunContext,
    note_id: str,
    body_md: str | None = None,
    title: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    user_id = run_context.user_id
    async with with_user_session(UUID(user_id)) as session:
        uc = UpdateNote(SqlAlchemyNoteRepository(session), ArqEmbeddingScheduler())
        uow = UnitOfWork(session)
        patch = {k: v for k, v in {"body_md": body_md, "title": title, "tags": tags}.items() if v is not None}
        result = await uc.execute(
            user_id=user_id, note_id=note_id, patch=patch, uow=uow
        )
        if result.is_failure:
            await uow.rollback()
            return {"ok": False, "error": str(result.error)}
        await uow.commit()
        return {"ok": True, "note": result.value}


@require_user_id
@tool(
    name="list_notes",
    description="List the user's notes, optionally filtered by tag.",
)
async def list_notes(
    run_context: RunContext,
    tag: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    user_id = run_context.user_id
    async with with_user_session(UUID(user_id)) as session:
        uc = ListNotes(SqlAlchemyNoteRepository(session))
        notes = await uc.execute(
            user_id=user_id, tags=[tag] if tag else None, limit=limit
        )
        return {"ok": True, "count": len(notes), "notes": notes}
