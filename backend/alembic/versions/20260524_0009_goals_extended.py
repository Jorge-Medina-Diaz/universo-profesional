"""goals — extend schema for lifecycle (status, target_date, details).

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-24

The initial `goals` table only had id/user_id/horizon/title/description.
We need:
  - `status` so we can track active vs paused vs completed vs dropped
  - `target_date` for deadline-based goals
  - `details` JSONB for sub-tasks / milestones / progress notes
  - `updated_at` / `completed_at` for lifecycle queries

We also add a small index for the common "active goals per user" query the
`goals_specialist` will run on every turn it gets routed.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "goals",
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
    )
    op.add_column(
        "goals",
        sa.Column("target_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "goals",
        sa.Column("details", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "goals",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "goals",
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_goals_user_status", "goals", ["user_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_goals_user_status", table_name="goals")
    op.drop_column("goals", "completed_at")
    op.drop_column("goals", "updated_at")
    op.drop_column("goals", "details")
    op.drop_column("goals", "target_date")
    op.drop_column("goals", "status")
