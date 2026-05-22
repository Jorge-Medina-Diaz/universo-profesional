"""architecture_decisions — ADRs as first-class entities.

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-28

Architecture decisions live in notes plain today. Promote them to a
dedicated table that enters ENTITY_REGISTRY: title + context + decision +
consequences + status (proposed|accepted|superseded) + optional linkage to
a project. The `architecture_specialist` (Sprint K) is its primary writer.

Coherence flows for free thanks to Sprint G's registry refactor: change
log, semantic dedup, mark_stale and curator all pick this up as soon as
the entity_type is in ENTITY_REGISTRY.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VECTOR_DIM = 1536


def upgrade() -> None:
    op.create_table(
        "architecture_decisions",
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
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("decision", sa.Text(), nullable=True),
        sa.Column("consequences", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="proposed"),
        sa.Column(
            "superseded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("architecture_decisions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "related_project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("embedding", Vector(VECTOR_DIM), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("visibility", sa.Text(), nullable=False, server_default="public"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("last_reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        "ix_architecture_decisions_user", "architecture_decisions", ["user_id"]
    )
    op.create_index(
        "ix_architecture_decisions_status",
        "architecture_decisions",
        ["user_id", "status"],
    )
    op.execute(
        "CREATE INDEX ix_architecture_decisions_tags "
        "ON architecture_decisions USING GIN(tags)"
    )
    op.execute(
        "CREATE INDEX ix_architecture_decisions_embedding "
        "ON architecture_decisions USING hnsw (embedding vector_cosine_ops)"
    )

    op.execute("ALTER TABLE architecture_decisions ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY architecture_decisions_user_isolation
            ON architecture_decisions
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS architecture_decisions_user_isolation "
        "ON architecture_decisions"
    )
    op.drop_table("architecture_decisions")
