"""Reconcile users.tier from subscriptions.plan (backfill).

Revision ID: 0031
Revises: 0030
Create Date: 2026-06-01

The Stripe webhook updated subscriptions.plan but never mirrored it onto
users.tier — the denormalized field every entitlement gate reads — so paying
users (especially 'premium', which users.tier couldn't even store before this
release) were locked out of paid features. The webhook now syncs tier going
forward; this migration backfills existing rows so current paying users get
access immediately and stale paid tiers are downgraded.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Root cause: ck_users_tier_value only allowed ('free','pro'), so 'premium'
    # could never be stored. Widen it FIRST, then backfill.
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_tier_value")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT ck_users_tier_value "
        "CHECK (tier IN ('free', 'pro', 'premium'))"
    )
    # Promote: active/trialing paid subscription → mirror plan onto tier.
    # subscriptions.plan is varchar, users.tier is text; IS DISTINCT FROM won't
    # implicitly cast across them, so cast both sides to text explicitly.
    op.execute(
        """
        UPDATE users u
        SET tier = s.plan::text, tier_updated_at = now()
        FROM subscriptions s
        WHERE s.user_id = u.id
          AND s.status IN ('active', 'trialing')
          AND s.plan IN ('pro', 'premium')
          AND u.tier::text IS DISTINCT FROM s.plan::text
          AND u.deleted_at IS NULL
        """
    )
    # Downgrade: tier says paid but no active paying subscription backs it.
    op.execute(
        """
        UPDATE users u
        SET tier = 'free', tier_updated_at = now()
        WHERE u.tier IN ('pro', 'premium')
          AND NOT EXISTS (
            SELECT 1 FROM subscriptions s
            WHERE s.user_id = u.id
              AND s.status IN ('active', 'trialing')
              AND s.plan IN ('pro', 'premium')
          )
        """
    )


def downgrade() -> None:
    # Data reconciliation — no meaningful inverse.
    pass
