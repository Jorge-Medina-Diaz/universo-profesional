"""rubric_documents + rubric_chunks — system rubrics corpus (RAG).

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-25

This is the storage for the system's curated rubrics — criteria, guiding
questions, seniority signals, anti-patterns and resources per software
sector. The corpus is global (no `user_id`, no RLS) — it's our source of
truth, identical for every user, edited by us in markdown and ingested
via the rubrics application ingest layer.

Two tables:
  - `rubric_documents` holds one row per .md file with full body + metadata
    + a "document-level" embedding for whole-doc semantic match.
  - `rubric_chunks` holds heading-aware chunks (one per `##` section)
    with their own embedding so the agent can retrieve the exact criteria
    / questions / signals section instead of the whole doc.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VECTOR_DIM = 1536


def upgrade() -> None:
    op.create_table(
        "rubric_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("sector", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("body_md", sa.Text(), nullable=False),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(VECTOR_DIM), nullable=True),
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

    op.create_table(
        "rubric_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rubric_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section_kind", sa.Text(), nullable=False),
        sa.Column("heading", sa.Text(), nullable=True),
        sa.Column("body_md", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(VECTOR_DIM), nullable=True),
        # denormalised for filter without join
        sa.Column("sector", sa.Text(), nullable=False),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_rubric_chunks_doc_idx"),
    )

    op.create_index("ix_rubric_docs_sector", "rubric_documents", ["sector"])
    op.create_index("ix_rubric_docs_slug", "rubric_documents", ["slug"])
    op.execute(
        "CREATE INDEX ix_rubric_docs_tags ON rubric_documents USING GIN (tags)"
    )
    op.execute(
        "CREATE INDEX ix_rubric_docs_embedding "
        "ON rubric_documents USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_index("ix_rubric_chunks_sector", "rubric_chunks", ["sector"])
    op.create_index("ix_rubric_chunks_kind", "rubric_chunks", ["section_kind"])
    op.execute(
        "CREATE INDEX ix_rubric_chunks_tags ON rubric_chunks USING GIN (tags)"
    )
    op.execute(
        "CREATE INDEX ix_rubric_chunks_embedding "
        "ON rubric_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS rubric_chunks CASCADE")
    op.execute("DROP TABLE IF EXISTS rubric_documents CASCADE")
