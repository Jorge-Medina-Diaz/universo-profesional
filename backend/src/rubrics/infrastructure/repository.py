"""SQLAlchemy repository for rubrics — upsert + retrieve + semantic search."""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.rubrics.domain.entities import RubricChunk, RubricDocument
from src.rubrics.infrastructure.orm import RubricChunkOrm, RubricDocumentOrm
from src.shared.security import utc_now


def _doc_to_entity(o: RubricDocumentOrm) -> RubricDocument:
    return RubricDocument(
        id=o.id,
        slug=o.slug,
        sector=o.sector,
        title=o.title,
        subtitle=o.subtitle,
        body_md=o.body_md,
        tags=list(o.tags or []),
        metadata=o.meta,
        version=o.version,
        content_hash=o.content_hash,
        embedding=list(o.embedding) if o.embedding is not None else None,
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


def _chunk_to_entity(o: RubricChunkOrm) -> RubricChunk:
    return RubricChunk(
        id=o.id,
        document_id=o.document_id,
        chunk_index=o.chunk_index,
        section_kind=o.section_kind,
        heading=o.heading,
        body_md=o.body_md,
        embedding=list(o.embedding) if o.embedding is not None else None,
        sector=o.sector,
        tags=list(o.tags or []),
    )


def _vec_literal(emb: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in emb) + "]"


class RubricRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_slug(self, slug: str) -> RubricDocument | None:
        row = (
            await self._session.execute(
                select(RubricDocumentOrm).where(RubricDocumentOrm.slug == slug)
            )
        ).scalar_one_or_none()
        return _doc_to_entity(row) if row else None

    async def upsert_document(
        self,
        doc: RubricDocument,
    ) -> tuple[RubricDocument, bool]:
        """Upsert by slug. Returns (entity, was_created)."""
        existing = (
            await self._session.execute(
                select(RubricDocumentOrm).where(RubricDocumentOrm.slug == doc.slug)
            )
        ).scalar_one_or_none()
        now = utc_now()
        if existing is None:
            row = RubricDocumentOrm(
                id=uuid4(),
                slug=doc.slug,
                sector=doc.sector,
                title=doc.title,
                subtitle=doc.subtitle,
                body_md=doc.body_md,
                tags=doc.tags,
                meta=doc.metadata,
                version=doc.version,
                content_hash=doc.content_hash,
                embedding=doc.embedding,
                created_at=now,
                updated_at=now,
            )
            self._session.add(row)
            await self._session.flush()
            return _doc_to_entity(row), True
        existing.sector = doc.sector
        existing.title = doc.title
        existing.subtitle = doc.subtitle
        existing.body_md = doc.body_md
        existing.tags = doc.tags
        existing.meta = doc.metadata
        existing.version = doc.version
        existing.content_hash = doc.content_hash
        if doc.embedding is not None:
            existing.embedding = doc.embedding
        existing.updated_at = now
        await self._session.flush()
        return _doc_to_entity(existing), False

    async def replace_chunks(
        self,
        document_id: UUID,
        chunks: list[RubricChunk],
    ) -> None:
        await self._session.execute(
            delete(RubricChunkOrm).where(RubricChunkOrm.document_id == document_id)
        )
        for c in chunks:
            self._session.add(
                RubricChunkOrm(
                    id=uuid4(),
                    document_id=document_id,
                    chunk_index=c.chunk_index,
                    section_kind=c.section_kind,
                    heading=c.heading,
                    body_md=c.body_md,
                    embedding=c.embedding,
                    sector=c.sector,
                    tags=c.tags,
                )
            )
        await self._session.flush()

    async def list_sectors(self) -> list[dict[str, Any]]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT sector, COUNT(*) AS n_docs "
                    "FROM rubric_documents WHERE deleted_at IS NULL "
                    "GROUP BY sector ORDER BY sector"
                )
            )
        ).all()
        return [{"sector": r[0], "doc_count": int(r[1])} for r in rows]

    async def list_documents(self, sector: str | None = None) -> list[RubricDocument]:
        stmt = select(RubricDocumentOrm).where(RubricDocumentOrm.deleted_at.is_(None))
        if sector:
            stmt = stmt.where(RubricDocumentOrm.sector == sector)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_doc_to_entity(r) for r in rows]

    async def search_chunks(
        self,
        query_embedding: list[float],
        *,
        sector: str | None = None,
        section_kind: str | None = None,
        tags: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        emb_literal = _vec_literal(query_embedding)
        clauses = ["rc.embedding IS NOT NULL"]
        params: dict[str, Any] = {"emb": emb_literal, "k": top_k}
        if sector:
            clauses.append("rc.sector = :sector")
            params["sector"] = sector
        if section_kind:
            clauses.append("rc.section_kind = :section_kind")
            params["section_kind"] = section_kind
        if tags:
            clauses.append("rc.tags && CAST(:tags AS text[])")
            params["tags"] = tags
        where_sql = " AND ".join(clauses)
        sql = text(
            f"""
            SELECT rc.id::text         AS chunk_id,
                   rc.document_id::text AS document_id,
                   rd.slug              AS slug,
                   rc.sector            AS sector,
                   rc.section_kind      AS section_kind,
                   rc.heading           AS heading,
                   rc.body_md           AS body_md,
                   rc.tags              AS tags,
                   1 - (rc.embedding <=> CAST(:emb AS vector)) AS score
              FROM rubric_chunks rc
              JOIN rubric_documents rd ON rd.id = rc.document_id
             WHERE {where_sql}
          ORDER BY rc.embedding <=> CAST(:emb AS vector)
             LIMIT :k
            """
        )
        rows = (await self._session.execute(sql, params)).mappings().all()
        return [dict(r) for r in rows]
