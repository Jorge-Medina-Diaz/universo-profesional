"""Per-user opt-out for reminder emails.

Revision ID: 0029
Revises: 0028
Create Date: 2026-05-29

The reminders engine now dispatches a daily digest email for due reminders
(cert expiring, stale course, …). Users must be able to turn that off. A
single boolean on `users` (default on) gates the dispatch; managed via
GET/PATCH /api/v1/users/me/notifications.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "notify_email_reminders",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "notify_email_reminders")
