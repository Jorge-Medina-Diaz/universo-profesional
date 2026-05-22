"""Semantic matcher — "is this new payload basically the same as an existing entry?".

Reuses the embedding service + the same `ENTITY_TABLES` mapping that powers
`PgVectorSemanticSearch`. Different from search: search returns top-k for a
user query; matching answers "do I already have this?" with a tight threshold.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from src.coherence.application.ports import SemanticMatcher
from src.shared.embeddings import get_embeddings_service
from src.universe.infrastructure.semantic_search import ENTITY_TABLES


# Cache of table → has-embedding-column, valid for the process lifetime
# (schema only changes via migrations, which restart the workers).
_HAS_EMBEDDING_CACHE: dict[str, bool] = {}


class PgVectorSemanticMatcher(SemanticMatcher):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._embedder = get_embeddings_service()

    async def _table_has_embedding(self, table: str) -> bool:
        cached = _HAS_EMBEDDING_CACHE.get(table)
        if cached is not None:
            return cached
        row = (
            await self._session.execute(
                sql_text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "  AND table_name = :t AND column_name = 'embedding'"
                ),
                {"t": table},
            )
        ).first()
        exists = row is not None
        _HAS_EMBEDDING_CACHE[table] = exists
        return exists

    async def find_most_similar(
        self,
        *,
        user_id: UUID,
        entity_type: str,
        text: str,
        threshold: float = 0.85,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        if entity_type not in ENTITY_TABLES:
            return []
        table, _fields = ENTITY_TABLES[entity_type]
        # Some entity tables (e.g. artifacts) have no embedding column —
        # they dedup by exact name only. Skip semantic matching cleanly
        # rather than emitting SQL that references a missing column.
        if not await self._table_has_embedding(table):
            return []
        embedding = await self._embedder.embed(text)
        # cosine similarity = 1 - cosine distance; pgvector `<=>` is distance.
        stmt = _build_match_stmt(table)
        rows = (
            await self._session.execute(
                stmt,
                {
                    "emb": _vec_literal(embedding),
                    "uid": str(user_id),
                    "k": top_k,
                },
            )
        ).all()
        out: list[dict[str, Any]] = []
        for r in rows:
            score = float(r.score)
            if score < threshold:
                break  # rows are ordered DESC by score
            out.append({"entity_id": r.id, "score": score})
        return out


def _build_match_stmt(table: str):  # type: ignore[no-untyped-def]
    # `table` comes from a closed-set (ENTITY_TABLES keys), safe to interpolate.
    return sql_text(
        f"""
        SELECT id::text AS id,
               1 - (embedding <=> CAST(:emb AS vector)) AS score
        FROM {table}
        WHERE user_id = :uid AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT :k
        """  # noqa: S608
    )


def _vec_literal(emb: list[float]) -> str:
    # pgvector accepts "[v1,v2,...]" string literals.
    return "[" + ",".join(f"{x:.7f}" for x in emb) + "]"
