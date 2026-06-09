"""Single-chat state endpoint.

The per-user chat is ONE persistent session (`session_id = main-<user_id>`).
This router exposes only `GET /api/v1/chat/state`, which returns:

  - the conversation digest — since P1.C this is agno's NATIVE session
    summary (`ai.agno_sessions.summary`, maintained by
    `enable_session_summaries` on every run), which replaced the custom
    sliding-window digest + its nightly cron,
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

from src.identity.interfaces.api.deps import CurrentUserId, SessionDep

router = APIRouter()


class ChatState(BaseModel):
    session_id: str
    digest: dict[str, Any] | None
    message_count: int


@router.get("/state", response_model=ChatState)
async def get_state(user_id: CurrentUserId, session: SessionDep) -> ChatState:
    sid = f"main-{user_id}"

    digest: dict[str, Any] | None = None
    msg_count = 0

    row = (
        await session.execute(
            text(
                "SELECT to_regclass('ai.agno_sessions') IS NOT NULL AS has_sessions, "
                "       to_regclass('public.agno_messages') IS NOT NULL AS has_msgs"
            )
        )
    ).first()
    if row is None:
        return ChatState(session_id=sid, digest=None, message_count=0)

    if row.has_sessions:
        summary = (
            await session.execute(
                text(
                    "SELECT summary FROM ai.agno_sessions "
                    "WHERE session_id = :sid AND user_id = :uid"
                ),
                {"sid": sid, "uid": str(user_id)},
            )
        ).scalar()
        # agno persists {"summary": str, "topics": [...]} — already the shape
        # the readable wants.
        if isinstance(summary, dict) and (summary.get("summary") or summary.get("topics")):
            digest = summary

    if row.has_msgs:
        c = (
            await session.execute(
                text("SELECT COUNT(*) AS n FROM agno_messages WHERE session_id = :sid"),
                {"sid": sid},
            )
        ).scalar()
        msg_count = int(c or 0)

    return ChatState(session_id=sid, digest=digest, message_count=msg_count)
