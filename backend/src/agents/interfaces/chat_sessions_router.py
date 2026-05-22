"""Single-chat state endpoint.

Sprint 4 collapses the per-user chat to ONE persistent session
(`session_id = main-<user_id>`). The previous multi-session CRUD is gone;
this router exposes only `GET /api/v1/chat/state`, which returns:

  - the digest of the conversation so far (if a digest workflow has run),
  - a count of messages persisted,
  - the deterministic `session_id` used by the AGUI router.

Frontend uses this to render the chat header, "you've talked X times" hints,
and to seed `useCopilotReadable` with the digest each turn.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from src.agents.memory.sliding_window import read_digest
from src.identity.interfaces.api.deps import CurrentUserId, SessionDep

router = APIRouter()


class ChatState(BaseModel):
    session_id: str
    digest: dict[str, Any] | None
    message_count: int


@router.get("/state", response_model=ChatState)
async def get_state(user_id: CurrentUserId, session: SessionDep) -> ChatState:
    sid = f"main-{user_id}"

    # digest lives in chat_session_meta.metadata.digest if/when the digest
    # workflow has run. The column itself was added in 0005; we wrap with
    # `to_regclass` so a fresh DB without ever having had a chat returns null.
    digest: dict[str, Any] | None = None
    msg_count = 0

    row = (
        await session.execute(
            text(
                "SELECT to_regclass('public.chat_session_meta') IS NOT NULL AS has_meta, "
                "       to_regclass('public.agno_messages') IS NOT NULL AS has_msgs"
            )
        )
    ).first()
    if row is None:
        return ChatState(session_id=sid, digest=None, message_count=0)

    # Meta digest (stored as JSONB column "metadata" key by the digest
    # workflow). The frontend injects this via useCopilotReadable so the
    # agent has a compact memory of everything older than the sliding
    # window — long conversations stay coherent without re-sending months
    # of raw turns.
    if row.has_meta:
        meta_row = (
            await session.execute(
                text(
                    "SELECT title FROM chat_session_meta "
                    "WHERE session_id = :sid AND user_id = :uid"
                ),
                {"sid": sid, "uid": user_id},
            )
        ).first()
        if meta_row is None:
            # First visit ever — create the row so subsequent UPSERTs work.
            await session.execute(
                text(
                    "INSERT INTO chat_session_meta (session_id, user_id, title) "
                    "VALUES (:sid, :uid, 'Universo profesional') "
                    "ON CONFLICT (session_id) DO NOTHING"
                ),
                {"sid": sid, "uid": user_id},
            )
            await session.commit()
        else:
            digest = await read_digest(
                session, user_id=str(user_id), session_id=sid
            )

    if row.has_msgs:
        c = (
            await session.execute(
                text("SELECT COUNT(*) AS n FROM agno_messages WHERE session_id = :sid"),
                {"sid": sid},
            )
        ).scalar()
        msg_count = int(c or 0)

    return ChatState(session_id=sid, digest=digest, message_count=msg_count)
