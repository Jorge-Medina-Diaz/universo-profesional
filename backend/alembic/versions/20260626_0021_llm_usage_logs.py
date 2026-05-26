"""LLM usage tracking table.

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-26

Tracks per-user token consumption and cost attribution for every agent run
and every document-generation LLM call. Enables quota enforcement and
spend visibility.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_logs",
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
        sa.Column("run_id", sa.String(64), nullable=True),
        sa.Column("session_id", sa.String(128), nullable=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "cache_read_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "cache_write_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(12, 8), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_llm_usage_logs_user_created", "llm_usage_logs", ["user_id", "created_at"])
    op.create_index("ix_llm_usage_logs_run", "llm_usage_logs", ["run_id"])
    op.execute("ALTER TABLE llm_usage_logs ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY llm_usage_logs_rls ON llm_usage_logs
            USING (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS llm_usage_logs_rls ON llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_run", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_user_created", table_name="llm_usage_logs")
    op.drop_table("llm_usage_logs")
