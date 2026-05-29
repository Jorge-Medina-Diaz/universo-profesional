"""Stripe webhook idempotency ledger.

Revision ID: 0028
Revises: 0027
Create Date: 2026-05-29

Stripe retries webhook delivery on any non-2xx/timeout, so the same event id
can arrive multiple times. This table records processed event ids so handlers
become idempotent (a duplicate checkout.session.completed must not upgrade a
user twice or double-send the receipt email).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stripe_processed_events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("event_type", sa.Text(), nullable=True),
        sa.Column(
            "processed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("stripe_processed_events")
