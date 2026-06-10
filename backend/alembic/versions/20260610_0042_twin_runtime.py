"""Public twin runtime: visitor sessions, question log, leads (TWIN_DESIGN §3.1).

Revision ID: 0042
Revises: 0041
Create Date: 2026-06-10

`user_id` on every table is the PROFILE OWNER (the tenant), not the visitor —
visitors are anonymous. Public-endpoint writes run inside
`with_user_session(owner_id)`, so the canonical RLS policy is the isolation
wall for twin traffic exactly as for the authenticated app. Transcript-ish
data (questions) is owner data under GDPR — cascades with the account.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0042"
down_revision: str | None = "0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CANONICAL_POLICY = (
    "(current_setting('app.bypass_rls'::text, true) = 'on' "
    "OR NULLIF(current_setting('app.current_user_id'::text, true), '')::uuid = user_id)"
)


def _rls(table: str) -> None:
    op.execute(
        f'CREATE POLICY "{table}_user_isolation" ON {table} '
        f"USING ({_CANONICAL_POLICY}) WITH CHECK ({_CANONICAL_POLICY})"
    )
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    op.create_table(
        "twin_sessions",
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
        sa.Column("visitor_hash", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("turns", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_twin_sessions_user", "twin_sessions", ["user_id", "started_at"])
    _rls("twin_sessions")

    op.create_table(
        "twin_questions",
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
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("twin_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answered", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_twin_questions_user", "twin_questions", ["user_id", "created_at"])
    _rls("twin_questions")

    op.create_table(
        "twin_leads",
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
        sa.Column("contact", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_twin_leads_user", "twin_leads", ["user_id", "created_at"])
    _rls("twin_leads")


def downgrade() -> None:
    op.drop_table("twin_leads")
    op.drop_table("twin_questions")
    op.drop_table("twin_sessions")
