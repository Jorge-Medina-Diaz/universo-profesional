"""Lifecycle Day-1 email sent marker (R19).

Revision ID: 0037
Revises: 0036
Create Date: 2026-06-01

A nullable timestamp on users so the Day-1 "finish your setup" lifecycle email
is sent at most once per user. Set by the lifecycle cron; never re-sent.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("day1_email_sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "day1_email_sent_at")
