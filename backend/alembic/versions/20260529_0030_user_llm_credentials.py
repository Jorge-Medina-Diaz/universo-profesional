"""BYOK: per-user encrypted LLM API keys.

Revision ID: 0030
Revises: 0029
Create Date: 2026-05-29

A Pro user can bring their own Anthropic/OpenAI key; the agent team is built
with it instead of the platform key. The key is Fernet-encrypted at rest. RLS
isolates rows per user (the resolver runs under with_user_session).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_llm_credentials",
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.execute("ALTER TABLE user_llm_credentials ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY user_llm_credentials_user_isolation ON user_llm_credentials
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_llm_credentials CASCADE")
