from __future__ import annotations

from collections.abc import Iterable
from uuid import NAMESPACE_URL, UUID, uuid5

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.application.retrieval._base import ScoredItem
from src.graph.application.retrieval._helpers import _attach_ranks
from src.shared.embeddings import get_embeddings_service

logger = structlog.get_logger(__name__)


class CommunityRetriever:
    name = "community"

    def __init__(self) -> None:
        self._embedder = get_embeddings_service()

    async def retrieve(
        self,
        session: AsyncSession,
        user_id: UUID,
        query: str,
        *,
        top_k: int = 12,
        kinds: Iterable[str] | None = None,
    ) -> list[ScoredItem]:
        try:
            embedding = await self._embedder.embed(query)
        except Exception as exc:
            logger.warning("community_retriever_embed_failed", error=str(exc))
            return []
        vec_literal = "[" + ",".join(f"{x:.7f}" for x in embedding) + "]"
        sql = (
            "SELECT community_id AS id, label, summary, "
            "1 - (embedding <=> CAST(:q AS vector)) AS score "
            "FROM community_summaries "
            "WHERE user_id = :uid "
            "  AND embedding IS NOT NULL "
            "ORDER BY embedding <=> CAST(:q AS vector) "
            "LIMIT :top_k"
        )
        rows = (
            await session.execute(
                text(sql),
                {"uid": str(user_id), "q": vec_literal, "top_k": top_k},
            )
        ).all()
        items: list[ScoredItem] = []
        for row in rows:
            # Communities are pseudo-entities: we synthesise a deterministic UUID
            # from the community_id string so downstream RRF treats them uniformly.
            pseudo_id = uuid5(NAMESPACE_URL, f"community:{row.id}")
            items.append(
                ScoredItem(
                    entity_id=pseudo_id,
                    kind="community",
                    name=str(row.label or ""),
                    score=float(row.score),
                    lane=self.name,
                    rationale=str(row.summary or ""),
                )
            )
        return _attach_ranks(items, lane=self.name)
