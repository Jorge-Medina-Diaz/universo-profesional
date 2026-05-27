from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.application.retrieval._base import ScoredItem
from src.graph.application.retrieval._helpers import _attach_ranks, _table_has_column
from src.graph.domain.registry import GRAPH_REGISTRY
from src.shared.embeddings import get_embeddings_service

logger = structlog.get_logger(__name__)


class DenseRetriever:
    name = "dense"

    def __init__(self) -> None:
        self._embedder = get_embeddings_service()

    async def retrieve(
        self,
        session: AsyncSession,
        user_id: UUID,
        query: str,
        *,
        top_k: int = 30,
        kinds: Iterable[str] | None = None,
    ) -> list[ScoredItem]:
        try:
            embedding = await self._embedder.embed(query)
        except Exception as exc:
            logger.warning("dense_retriever_embed_failed", error=str(exc))
            return []
        vec_literal = "[" + ",".join(f"{x:.7f}" for x in embedding) + "]"
        kinds_list = list(kinds) if kinds else list(GRAPH_REGISTRY.keys())

        # See BM25Retriever for the rationale on sequential per-kind queries.
        merged: list[ScoredItem] = []
        for kind in kinds_list:
            batch = await self._search_one_kind(
                session,
                user_id=user_id,
                kind=kind,
                vec_literal=vec_literal,
                top_k=top_k,
            )
            merged.extend(batch)
        merged.sort(key=lambda x: x.score, reverse=True)
        return _attach_ranks(merged[:top_k], lane=self.name)

    async def _search_one_kind(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
        kind: str,
        vec_literal: str,
        top_k: int,
    ) -> list[ScoredItem]:
        cfg = GRAPH_REGISTRY.get(kind)
        if cfg is None:
            return []
        if not await _table_has_column(session, cfg.sql_table, "embedding"):
            # Some kinds (artifact, architecture_decision in earlier
            # schemas) don't yet have an embedding column. The dense
            # lane just skips them — BM25 + PPR still cover the table.
            return []
        sql = (
            f"SELECT id::text AS id, {cfg.name_field} AS name, "
            f"1 - (embedding <=> CAST(:q AS vector)) AS score "
            f"FROM {cfg.sql_table} "
            f"WHERE user_id = :uid "
            f"  AND deleted_at IS NULL "
            f"  AND embedding IS NOT NULL "
            f"ORDER BY embedding <=> CAST(:q AS vector) "
            f"LIMIT :top_k"
        )
        rows = (
            await session.execute(
                text(sql),
                {"uid": str(user_id), "q": vec_literal, "top_k": top_k},
            )
        ).all()
        return [
            ScoredItem(
                entity_id=UUID(row.id),
                kind=kind,
                name=str(row.name or ""),
                score=float(row.score),
                lane=self.name,
            )
            for row in rows
        ]
