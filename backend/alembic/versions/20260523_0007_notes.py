"""notes (narrative biographical layer).

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-23

The 4-memory-layers architecture (see docs/architecture/memory-layers.md)
needs a narrative tier between rigid universe entities (skill/experience/...)
and Agno's atomic memories. Notes are markdown blobs with tags and optional
evidence links to any universe entity. Used for: "estoy estudiando RAG",
opinions, learning threads, biographical context.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VECTOR_DIM = 1536


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body_md", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("source", sa.Text(), nullable=False, server_default="agent_chat"),
        sa.Column("source_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("visibility", sa.Text(), nullable=False, server_default="private"),
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
        sa.Column("last_reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_index("ix_notes_user_updated", "notes", ["user_id", "updated_at"])
    op.execute("CREATE INDEX ix_notes_user_tags ON notes USING GIN (tags)")
    op.execute(
        "CREATE INDEX ix_notes_embedding ON notes USING hnsw (embedding vector_cosine_ops)"
    )

    op.execute("ALTER TABLE notes ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY notes_user_isolation ON notes
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notes CASCADE")
