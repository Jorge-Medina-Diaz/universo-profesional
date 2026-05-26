"""SQLAlchemy ORM for rubric_documents + rubric_chunks."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db import Base
from src.shared.embeddings import EMBEDDING_DIM


class RubricDocumentOrm(Base):
    __tablename__ = "rubric_documents"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    sector: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    subtitle: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    # `metadata` is reserved by SQLAlchemy's Declarative on Base — use a python
    # attribute alias and map it to the real column name.
    meta: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class RubricChunkOrm(Base):
    __tablename__ = "rubric_chunks"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    document_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("rubric_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_kind: Mapped[str] = mapped_column(Text, nullable=False)
    heading: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    sector: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_rubric_chunks_doc_idx"),
    )
