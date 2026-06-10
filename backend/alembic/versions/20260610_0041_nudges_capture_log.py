"""Proactive KB loop substrate: nudges + capture_log (P3.A).

Revision ID: 0041
Revises: 0040
Create Date: 2026-06-10

- `nudges`: typed proactive prompts ("¿qué has hecho esta semana?", goal
  check-ins, pending curation, stale entities). One row per (user, kind,
  dedupe_key); the eligibility engine inserts `pending`, the FE surfaces
  them as composer chips / Home badge, the user acts or dismisses. Cooldowns
  live in the engine; dedupe_key makes re-sweeps idempotent.
- `capture_log`: the anti-repetition memory — every discovery question the
  agent asks (hashed) so neither the nudge engine nor
  suggest_discovery_questions ever re-asks something covered <30 days ago.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0041"
down_revision: str | None = "0040"
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
        "nudges",
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
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("dedupe_key", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("surfaced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "kind", "dedupe_key", name="uq_nudges_dedupe"),
        sa.CheckConstraint(
            "status IN ('pending','surfaced','acted','dismissed','expired')",
            name="ck_nudges_status",
        ),
    )
    op.create_index(
        "ix_nudges_user_active",
        "nudges",
        ["user_id", "status"],
        postgresql_where=sa.text("status IN ('pending','surfaced')"),
    )
    _rls("nudges")

    op.create_table(
        "capture_log",
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
        sa.Column("question_hash", sa.Text(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=True),
        sa.Column(
            "asked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("answered", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_capture_log_user_hash", "capture_log", ["user_id", "question_hash"]
    )
    _rls("capture_log")


def downgrade() -> None:
    op.drop_table("capture_log")
    op.drop_table("nudges")
