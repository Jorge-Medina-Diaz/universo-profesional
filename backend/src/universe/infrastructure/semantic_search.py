"""Semantic search over universe entities using pgvector cosine + RRF rerank."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.universe.application.ports import SemanticSearchPort

# Cache of table → has-embedding-column, valid for the process lifetime
# (schema only changes via migrations, which restart the workers).
_HAS_EMBEDDING_CACHE: dict[str, bool] = {}


ENTITY_TABLES = {
    "education": ("educations", ["institution", "degree", "field_of_study", "description"]),
    "experience": ("experiences", ["organization", "role", "description"]),
    "project": ("projects", ["name", "description", "impact"]),
    "skill": ("skills", ["name", "category", "level"]),
    "certification": ("certifications", ["name", "issuer"]),
    "course": ("courses", ["title", "platform"]),
    "language": ("languages", ["code", "name", "level"]),
    "achievement": ("achievements", ["title", "description"]),
    "interest": ("interests", ["name", "description"]),
    # Sprint G — portfolio artifacts (github_repo|talk|blog_post|...)
    "artifact": ("artifacts", ["type", "title", "url", "description"]),
    # Sprint K — architecture decision records
    "architecture_decision": (
        "architecture_decisions",
        ["title", "context", "decision", "consequences", "status"],
    ),
}


class PgVectorSemanticSearch(SemanticSearchPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _table_has_embedding(self, table: str) -> bool:
        cached = _HAS_EMBEDDING_CACHE.get(table)
        if cached is not None:
            return cached
        row = (
            await self._session.execute(
                text(
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

    async def search(
        self,
        *,
        user_id: UUID,
        embedding: list[float],
        top_k: int = 30,
        entity_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        chosen = entity_types or list(ENTITY_TABLES.keys())
        results: list[dict[str, Any]] = []
        # We query each table independently and then merge by score.
        # For MVP scope this is simpler than a UNION ALL with parameter rewriting.
        for et in chosen:
            if et not in ENTITY_TABLES:
                continue
            table, fields = ENTITY_TABLES[et]
            # Some entity tables (e.g. artifacts) have no embedding column —
            # skip them cleanly instead of emitting SQL that references a
            # missing column (which 500s the whole request).
            if not await self._table_has_embedding(table):
                continue
            fields_sql = ", ".join(fields)
            stmt = text(
                f"""
                SELECT id::text AS id,
                       {fields_sql},
                       1 - (embedding <=> CAST(:emb AS vector)) AS score
                FROM {table}
                WHERE user_id = :uid
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:emb AS vector)
                LIMIT :k
                """  # noqa: S608
            )
            rows = (
                await self._session.execute(
                    stmt,
                    {"emb": str(embedding), "uid": str(user_id), "k": top_k},
                )
            ).all()
            for r in rows:
                fields_dict = {f: getattr(r, f, None) for f in fields}
                results.append(
                    {
                        "entity_type": et,
                        "entity_id": r.id,
                        "score": float(r.score),
                        "fields": fields_dict,
                    }
                )
        # Reciprocal Rank Fusion across entity types
        # For MVP we just sort by raw cosine score; RRF kicks in when we have
        # multiple ranked lists (BM25 + semantic) — wire BM25 in v1.
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
