"""Chat sessions UX metadata (title / pinned / archived).

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-22

Agno persists session content (messages, memories, knowledge chunks) in its own
tables created via `PostgresDb.create_tables()` at app startup. This migration
adds a small auxiliary table for purely UX concerns — what the user titled the
session, whether they pinned it to the top, whether they archived it.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_session_meta",
        sa.Column("session_id", sa.Text(), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
    )
    op.create_index(
        "ix_chat_session_meta_user_updated",
        "chat_session_meta",
        ["user_id", "updated_at"],
    )
    op.execute("ALTER TABLE chat_session_meta ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY chat_session_meta_user_isolation ON chat_session_meta
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chat_session_meta CASCADE")
