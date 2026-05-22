"""User subscription tier (free / pro).

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-21

Adds a `tier` column to `users` so we can gate premium features (LinkedIn
Proxycurl import, larger CV exports, future job-search integrations) without
needing Stripe wired up yet. Tier is plain TEXT (not ENUM) for forward
compatibility — adding new tiers won't require a DDL migration.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("tier", sa.Text(), nullable=False, server_default="free"),
    )
    op.add_column(
        "users",
        sa.Column("tier_updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_users_tier_value",
        "users",
        "tier IN ('free', 'pro')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_tier_value", "users", type_="check")
    op.drop_column("users", "tier_updated_at")
    op.drop_column("users", "tier")
