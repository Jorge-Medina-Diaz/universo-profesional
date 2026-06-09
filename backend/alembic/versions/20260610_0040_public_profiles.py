"""Public digital twin groundwork: public_profiles table (design phase 4).

Revision ID: 0040
Revises: 0039
Create Date: 2026-06-10

Schema-only groundwork for docs/TWIN_DESIGN.md — no endpoints, no UI yet.
`enabled` defaults false and nothing reads the table, so this is inert until
the twin build is greenlit. Shipping it now means the implementation cycle
starts without a schema dance.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0040"
down_revision: str | None = "0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CANONICAL_POLICY = (
    "(current_setting('app.bypass_rls'::text, true) = 'on' "
    "OR NULLIF(current_setting('app.current_user_id'::text, true), '')::uuid = user_id)"
)


def upgrade() -> None:
    op.create_table(
        "public_profiles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        # Default-deny curation: kind toggles, per-entity overrides, redaction
        # flags, owner charter — shape defined in docs/TWIN_DESIGN.md §3.1.
        sa.Column(
            "curation",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        'CREATE POLICY "public_profiles_user_isolation" ON public_profiles '
        f"USING ({_CANONICAL_POLICY}) WITH CHECK ({_CANONICAL_POLICY})"
    )
    op.execute("ALTER TABLE public_profiles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public_profiles FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("public_profiles")
