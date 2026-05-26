"""Knowledge store — ingest, search, list (raw SQL + pgvector + RLS).

Mirrors the codebase conventions: functions take an AsyncSession, set the
RLS user themselves (so callers can't accidentally leak across tenants),
and use the shared embeddings provider. The graph hybrid retriever covers
structured entities; this covers long unstructured documents.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.db import set_rls_user
from src.shared.embeddings import get_embeddings_provider

logger = structlog.get_logger(__name__)

# Chunking: ~1000 chars with 150 overlap. Big enough to keep a coherent
# passage, small enough that a single chunk embeds meaningfully.
_CHUNK_TARGET = 1000
_CHUNK_OVERLAP = 150
_MAX_CHARS = 400_000  # hard cap per document (~100k tokens) to bound cost


def _vec_literal(emb: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in emb) + "]"


def chunk_text(body: str, *, target: int = _CHUNK_TARGET, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks on paragraph/whitespace boundaries."""
    body = (body or "").strip()
    if not body:
        return []
    if len(body) <= target:
        return [body]
    chunks: list[str] = []
    start = 0
    n = len(body)
    while start < n:
        end = min(start + target, n)
        # Prefer to break on a paragraph or sentence boundary near the end.
        if end < n:
            window = body[start:end]
            for sep in ("\n\n", "\n", ". ", " "):
                idx = window.rfind(sep)
                if idx > target * 0.5:
                    end = start + idx + len(sep)
                    break
        chunk = body[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


async def ingest_document(
    session: AsyncSession,
    *,
    user_id: UUID,
    title: str,
    body: str,
    source: str = "upload",
    source_uri: str | None = None,
    mime: str | None = None,
    tags: list[str] | None = None,
) -> UUID | None:
    """Chunk + embed + store a document. Returns the document id, or None
    when there's nothing to ingest (empty body)."""
    await set_rls_user(session, user_id)
    body = (body or "").strip()
    if len(body) > _MAX_CHARS:
        body = body[:_MAX_CHARS]
    chunks = chunk_text(body)
    if not chunks:
        return None

    doc_row = (
        await session.execute(
            text(
                """
                INSERT INTO knowledge_documents
                    (user_id, title, source, source_uri, mime, char_count,
                     chunk_count, status, tags)
                VALUES (:uid, :title, :source, :uri, :mime, :chars, :n,
                        'ingested', :tags)
                RETURNING id::text AS id
                """
            ),
            {
                "uid": str(user_id),
                "title": title[:500] if title else "documento",
                "source": source,
                "uri": source_uri,
                "mime": mime,
                "chars": len(body),
                "n": len(chunks),
                "tags": tags or [],
            },
        )
    ).first()
    doc_id = UUID(doc_row.id)

    provider = get_embeddings_provider()
    try:
        embeddings = await provider.embed_batch(chunks)
    except Exception as exc:
        logger.warning("knowledge_embed_failed", error=str(exc))
        embeddings = [None] * len(chunks)  # type: ignore[list-item]

    for idx, chunk in enumerate(chunks):
        emb = embeddings[idx] if idx < len(embeddings) else None
        await session.execute(
            text(
                """
                INSERT INTO knowledge_chunks
                    (document_id, user_id, chunk_index, content, embedding)
                VALUES (:did, :uid, :idx, :content,
                        CAST(:emb AS vector))
                """
            ),
            {
                "did": str(doc_id),
                "uid": str(user_id),
                "idx": idx,
                "content": chunk,
                "emb": _vec_literal(emb) if emb else None,
            },
        )
    logger.info(
        "knowledge_ingested",
        user_id=str(user_id),
        document_id=str(doc_id),
        chunks=len(chunks),
        source=source,
    )
    return doc_id


async def search_knowledge(
    session: AsyncSession,
    *,
    user_id: UUID,
    query: str,
    top_k: int = 5,
    tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Semantic search over the user's knowledge chunks (RLS-scoped)."""
    await set_rls_user(session, user_id)
    if not (query or "").strip():
        return []
    provider = get_embeddings_provider()
    try:
        q_vec = await provider.embed(query)
    except Exception as exc:
        logger.warning("knowledge_query_embed_failed", error=str(exc))
        return []

    tag_filter = ""
    params: dict[str, Any] = {"q": _vec_literal(q_vec), "k": top_k}
    if tags:
        tag_filter = "AND d.tags && :tags"
        params["tags"] = tags

    rows = (
        await session.execute(
            text(
                f"""
                SELECT c.document_id::text AS document_id,
                       d.title AS title,
                       c.chunk_index AS chunk_index,
                       c.content AS content,
                       1 - (c.embedding <=> CAST(:q AS vector)) AS score
                FROM knowledge_chunks c
                JOIN knowledge_documents d ON d.id = c.document_id
                WHERE c.embedding IS NOT NULL
                  AND d.deleted_at IS NULL
                  {tag_filter}
                ORDER BY c.embedding <=> CAST(:q AS vector)
                LIMIT :k
                """
            ),
            params,
        )
    ).all()
    return [
        {
            "document_id": r.document_id,
            "title": r.title,
            "chunk_index": r.chunk_index,
            "content": r.content,
            "score": round(float(r.score), 4),
        }
        for r in rows
    ]


async def list_documents(
    session: AsyncSession, *, user_id: UUID
) -> list[dict[str, Any]]:
    await set_rls_user(session, user_id)
    rows = (
        await session.execute(
            text(
                """
                SELECT id::text AS id, title, source, mime, char_count,
                       chunk_count, status, tags, created_at
                FROM knowledge_documents
                WHERE deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT 100
                """
            )
        )
    ).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "source": r.source,
            "mime": r.mime,
            "char_count": r.char_count,
            "chunk_count": r.chunk_count,
            "status": r.status,
            "tags": list(r.tags or []),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
