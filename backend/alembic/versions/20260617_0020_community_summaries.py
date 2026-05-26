"""Community summaries table with pgvector HNSW.

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-17

Adds a relational sidecar `community_summaries` that mirrors the :Community
vertices in AGE but carries a pgvector embedding so the retrieval pipeline
can query communities via HNSW k-NN (the 4th lane of hybrid retrieval).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "community_summaries",
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
        sa.Column("community_id", sa.String(128), nullable=False),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "member_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # Convert ARRAY(float) to pgvector(1536) for HNSW indexing.
    op.execute(
        "ALTER TABLE community_summaries "
        "ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)"
    )
    op.create_index(
        "ix_community_summaries_user",
        "community_summaries",
        ["user_id", "community_id"],
    )
    op.execute(
        "CREATE INDEX ix_community_summaries_hnsw "
        "ON community_summaries USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute("ALTER TABLE community_summaries ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY community_summaries_rls ON community_summaries
            USING (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS community_summaries_rls ON community_summaries")
    op.execute("DROP INDEX IF EXISTS ix_community_summaries_hnsw")
    op.drop_index("ix_community_summaries_user", table_name="community_summaries")
    op.drop_table("community_summaries")
