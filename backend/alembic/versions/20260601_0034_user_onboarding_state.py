"""Server-side onboarding/activation state on users.

Revision ID: 0034
Revises: 0033
Create Date: 2026-06-01

Onboarding-completion lived only in the browser's localStorage — invisible
cross-device and to lifecycle emails. Persist it server-side:
onboarding_started_at / activated_at / onboarding_completed_at. Existing users
are backfilled from their real data so they are not bounced back into the wizard.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarding_started_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("activated_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("onboarding_completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    # Existing users started onboarding when they registered.
    op.execute(
        "UPDATE users SET onboarding_started_at = created_at "
        "WHERE onboarding_started_at IS NULL"
    )
    # Mark already-active users activated + completed so they keep skipping the
    # wizard (activation = >=1 experience OR >=3 skills OR 1 CV).
    op.execute(
        """
        UPDATE users u SET activated_at = now(), onboarding_completed_at = now()
        WHERE u.activated_at IS NULL AND (
            EXISTS (SELECT 1 FROM experiences e WHERE e.user_id = u.id)
            OR (SELECT count(*) FROM skills s WHERE s.user_id = u.id) >= 3
            OR EXISTS (SELECT 1 FROM documents d WHERE d.user_id = u.id AND d.kind = 'cv')
        )
        """
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed_at")
    op.drop_column("users", "activated_at")
    op.drop_column("users", "onboarding_started_at")
