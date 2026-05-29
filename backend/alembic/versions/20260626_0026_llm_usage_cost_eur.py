"""LLM usage tracking: EUR cost + agent column.

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-26

1. Renames cost_usd → cost_eur to match the new EUR-first pricing.
2. Adds `agent` column for per-specialist breakdown.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rename cost_usd → cost_eur
    op.alter_column("llm_usage_logs", "cost_usd", new_column_name="cost_eur")

    # Add agent column
    op.add_column(
        "llm_usage_logs",
        sa.Column("agent", sa.String(64), nullable=True),
    )
    op.create_index("ix_llm_usage_logs_agent", "llm_usage_logs", ["agent"])


def downgrade() -> None:
    op.drop_index("ix_llm_usage_logs_agent", table_name="llm_usage_logs")
    op.drop_column("llm_usage_logs", "agent")
    op.alter_column("llm_usage_logs", "cost_eur", new_column_name="cost_usd")
