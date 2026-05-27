from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.application.retrieval._base import ScoredItem
from src.graph.application.retrieval._helpers import _attach_ranks
from src.graph.domain.registry import GRAPH_REGISTRY


class BM25Retriever:
    name = "bm25"

    async def retrieve(
        self,
        session: AsyncSession,
        user_id: UUID,
        query: str,
        *,
        top_k: int = 30,
        kinds: Iterable[str] | None = None,
    ) -> list[ScoredItem]:
        kinds_list = list(kinds) if kinds else list(GRAPH_REGISTRY.keys())
        # asyncpg permits only one operation per connection at a time,
        # so per-kind queries run sequentially. The GIN(tsv) index keeps
        # each one ~3 ms, so 11 kinds = ~30 ms — well within budget.
        merged: list[ScoredItem] = []
        for kind in kinds_list:
            batch = await self._search_one_kind(
                session, user_id=user_id, kind=kind, query=query, top_k=top_k
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
        query: str,
        top_k: int,
    ) -> list[ScoredItem]:
        cfg = GRAPH_REGISTRY.get(kind)
        if cfg is None:
            return []
        sql = (
            f"SELECT id::text AS id, {cfg.name_field} AS name, "
            f"ts_rank_cd(tsv, plainto_tsquery('spanish', :q)) AS score "
            f"FROM {cfg.sql_table} "
            f"WHERE user_id = :uid "
            f"  AND deleted_at IS NULL "
            f"  AND tsv @@ plainto_tsquery('spanish', :q) "
            f"ORDER BY score DESC LIMIT :top_k"
        )
        rows = (
            await session.execute(
                text(sql), {"uid": str(user_id), "q": query, "top_k": top_k}
            )
        ).all()
        return [
            ScoredItem(
                entity_id=UUID(row.id),
                kind=kind,
                name=str(row.name or ""),
                score=float(row.score or 0.0),
                lane=self.name,
            )
            for row in rows
        ]
