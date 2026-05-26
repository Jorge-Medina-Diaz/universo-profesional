"""Sliding window + digest for the single-chat model.

Agno's `agno_messages` table stores everything forever. To keep the context
sent to the LLM bounded — and to give the agent a sense of "what we've been
talking about over months" — we maintain a small structured digest of all
messages OLDER than the window. The window itself (last N=40) stays as raw
messages in the prompt; older content lives only in the digest.

The digest is refreshed by `session_digest_workflow`. The frontend can ask
for it via `/api/v1/chat/state` and inject it via `useCopilotReadable`.

Both helpers below are pure DB plumbing — the LLM-driven summarization lives
in the workflow file alongside the cron registration.

COEXISTENCE with Agno v2.6.9 native memory:
- `enable_session_summaries=True` on the Team gives Agno lightweight
  per-session summaries managed by the framework.
- `enable_user_memories=True` gives Agno atomic user memories.
- This module does something different: it produces a long-horizon digest
  that the frontend explicitly injects as a CopilotReadable.  It therefore
  coexists with the native layer rather than replacing it.
- Deprecation TODO: once we validate that Agno's native summaries alone
  keep the context window bounded AND the frontend no longer needs the
  explicit digest injection, this module can be retired.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


WINDOW_SIZE = 40
DIGEST_THRESHOLD = WINDOW_SIZE + 20  # accumulate buffer before recomputing


async def messages_to_digest(
    session: AsyncSession, *, session_id: str
) -> list[dict[str, Any]] | None:
    """Return the older messages that should be folded into the digest.

    Returns None when the total count is under DIGEST_THRESHOLD (nothing to do).
    """
    count_row = (
        await session.execute(
            text("SELECT COUNT(*) AS n FROM agno_messages WHERE session_id = :sid"),
            {"sid": session_id},
        )
    ).first()
    total = int(count_row.n if count_row else 0)
    if total < DIGEST_THRESHOLD:
        return None
    # Keep the most recent `WINDOW_SIZE` rows raw; digest everything older.
    older_n = total - WINDOW_SIZE
    rows = (
        await session.execute(
            text(
                "SELECT role, content::text AS content FROM agno_messages "
                "WHERE session_id = :sid "
                "ORDER BY created_at ASC LIMIT :limit"
            ),
            {"sid": session_id, "limit": older_n},
        )
    ).all()
    return [{"role": r.role, "content": r.content} for r in rows]


async def store_digest(
    session: AsyncSession,
    *,
    user_id: str,
    session_id: str,
    digest: dict[str, Any],
) -> None:
    """Persist the digest payload into chat_session_meta.metadata.

    We piggy-back on the existing `title` row (one per user) by adding a
    `metadata` column at first use. ALTER TABLE inside transaction is fine
    against Postgres and idempotent.
    """
    await session.execute(
        text(
            "ALTER TABLE chat_session_meta "
            "ADD COLUMN IF NOT EXISTS metadata JSONB"
        )
    )
    import json

    await session.execute(
        text(
            """
            INSERT INTO chat_session_meta (session_id, user_id, title, metadata)
            VALUES (:sid, :uid, 'Universo profesional', CAST(:m AS jsonb))
            ON CONFLICT (session_id) DO UPDATE
              SET metadata = CAST(:m AS jsonb), updated_at = now()
            """
        ),
        {
            "sid": session_id,
            "uid": user_id,
            "m": json.dumps({"digest": digest}),
        },
    )


async def read_digest(
    session: AsyncSession, *, user_id: str, session_id: str
) -> dict[str, Any] | None:
    # The `metadata` column is added lazily on first write_digest(). Reading
    # before any digest has ever been written would 500 on a missing column,
    # so guard on its existence and degrade to "no digest yet".
    has_col = (
        await session.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'chat_session_meta' "
                "  AND column_name = 'metadata'"
            )
        )
    ).first()
    if has_col is None:
        return None
    row = (
        await session.execute(
            text(
                "SELECT metadata FROM chat_session_meta "
                "WHERE session_id = :sid AND user_id = :uid"
            ),
            {"sid": session_id, "uid": user_id},
        )
    ).first()
    if row is None or row.metadata is None:
        return None
    return row.metadata.get("digest") if isinstance(row.metadata, dict) else None
