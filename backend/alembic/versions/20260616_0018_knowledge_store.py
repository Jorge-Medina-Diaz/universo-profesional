"""knowledge store — long-document substrate (memory layer 4).

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-16

Memory layer 4 (knowledge: PDFs / papers / long docs) was declared in the
agent's prompt but never built — `search_knowledge` was a no-op stub. This
adds the native substrate: per-user documents chunked + embedded over
pgvector, isolated by RLS like every other tenant table. The substrate is
"coherence-aligned": ingestion also feeds the coherence engine (entity
extraction), so the graph stays the source of truth and the raw text stays
re-processable.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VECTOR_DIM = 1536


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        # Where it came from: 'pdf_import' | 'upload' | 'paper' | 'manual' …
        sa.Column("source", sa.Text(), nullable=False, server_default="upload"),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("mime", sa.Text(), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        # 'ingested' once chunks+embeddings are in; 'extracting'/'extracted'
        # track the coherence pass that pulls entities into the universe.
        sa.Column("status", sa.Text(), nullable=False, server_default="ingested"),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_knowledge_documents_user", "knowledge_documents", ["user_id", "created_at"]
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Denormalised user_id so the RLS policy and search filter stay on a
        # single table without a join.
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(VECTOR_DIM), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name="uq_knowledge_chunk_idx"
        ),
    )
    op.create_index(
        "ix_knowledge_chunks_doc", "knowledge_chunks", ["document_id", "chunk_index"]
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding ON knowledge_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    for table in ("knowledge_documents", "knowledge_chunks"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_user_isolation ON {table}
            USING (user_id = current_setting('app.current_user_id', true)::uuid)
            WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
            """
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS knowledge_chunks CASCADE")
    op.execute("DROP TABLE IF EXISTS knowledge_documents CASCADE")
