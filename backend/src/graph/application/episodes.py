"""Episode tracker — every chat session becomes a temporal node.

Sprint P of the v2 plan. An Episode is a per-session vertex in the
personal graph that other entities link to via :TOUCHED_IN edges. The
result is a Graphiti-style "what happened in this session" subgraph
that powers:

  • The Trajectory lens in the UI (timeline of episodes + entities).
  • Curator's "you haven't touched X since {episode}" nudges.
  • Coordinator's "we discussed X two sessions ago — want to refine?"
    suggestions.

We use the existing `chat_session_meta` row as the canonical session
identifier (one row per Agno session). The Episode vertex's `id`
matches the session UUID so the chat → graph bridge stays trivial.

API:
  • `ensure_episode(session, user_id, chat_session_id)` — idempotent,
    creates the Episode vertex on first call and returns its id.
  • `record_touch(session, user_id, chat_session_id, entity_id)` —
    creates a :TOUCHED_IN edge from the entity to the episode.
  • `close_episode(...)` — sets ended_at; the LLM summary is computed
    lazily by an arq task to keep the chat-close path fast.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.domain import schema
from src.graph.infrastructure.age_client import cypher

logger = structlog.get_logger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


async def ensure_episode(
    session: AsyncSession,
    *,
    user_id: UUID,
    chat_session_id: str,
) -> UUID:
    """Create or fetch the Episode vertex for this chat session.

    The Episode id is derived deterministically from (user_id,
    chat_session_id) so the operation is idempotent — two concurrent
    writers won't create duplicate vertices and two users with colliding
    session ids land on disjoint Episode vertices.
    """
    episode_id = _episode_uuid_for(user_id, chat_session_id)
    await cypher(
        session,
        schema.GRAPH_PERSONAL,
        """
        MERGE (ep:Episode {id: $eid, user_id: $uid})
        SET ep.chat_session_id = $cid,
            ep.started_at = COALESCE(ep.started_at, $now),
            ep.updated_at = $now
        RETURN ep
        """,
        params={
            "eid": str(episode_id),
            "uid": str(user_id),
            "cid": chat_session_id,
            "now": _now_iso(),
        },
    )
    return episode_id


async def record_touch(
    session: AsyncSession,
    *,
    user_id: UUID,
    chat_session_id: str,
    entity_id: UUID,
) -> None:
    """Materialise the (:Entity)-[:TOUCHED_IN]->(:Episode) edge.

    Idempotent — MERGE on the pattern with COALESCE on valid_from. The
    edge carries valid_from for timeline queries and `chat_session_id`
    redundantly so curator queries can filter without traversing.
    """
    episode_id = await ensure_episode(
        session, user_id=user_id, chat_session_id=chat_session_id
    )
    await cypher(
        session,
        schema.GRAPH_PERSONAL,
        """
        MATCH (e {id: $eid, user_id: $uid}),
              (ep:Episode {id: $epid, user_id: $uid})
        MERGE (e)-[r:TOUCHED_IN]->(ep)
        SET r.valid_from = COALESCE(r.valid_from, $now),
            r.updated_at = $now
        """,
        params={
            "eid": str(entity_id),
            "epid": str(episode_id),
            "uid": str(user_id),
            "now": _now_iso(),
        },
    )


async def close_episode(
    session: AsyncSession,
    *,
    user_id: UUID,
    chat_session_id: str,
    summary: str | None = None,
) -> None:
    """Mark an Episode as finished. Sets ended_at and optional summary."""
    episode_id = _episode_uuid_for(user_id, chat_session_id)
    await cypher(
        session,
        schema.GRAPH_PERSONAL,
        """
        MATCH (ep:Episode {id: $eid, user_id: $uid})
        SET ep.ended_at = $now,
            ep.summary = $summary
        """,
        params={
            "eid": str(episode_id),
            "uid": str(user_id),
            "now": _now_iso(),
            "summary": summary,
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _episode_uuid_for(user_id: UUID, chat_session_id: str) -> UUID:
    """Deterministic UUID derived from (user_id, chat_session_id).

    Including `user_id` in the digest guarantees that two users can never
    share the same Episode vertex id — even if their chat_session_ids
    collide (a vanishingly rare UUID4 collision, but the previous version
    relied on the MERGE predicate as the only line of defence and broke
    the "Episode id is globally unique" invariant).
    """
    import hashlib

    digest = hashlib.sha256(
        f"episode:{user_id}:{chat_session_id}".encode()
    ).digest()[:16]
    return UUID(bytes=digest)
