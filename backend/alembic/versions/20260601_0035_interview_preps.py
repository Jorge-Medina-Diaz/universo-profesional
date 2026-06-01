"""Interview-prep artifacts per job (research brief, question bank, STAR drafts).

Revision ID: 0035
Revises: 0034
Create Date: 2026-06-01

R16: persist per-application interview preparation. One row per (user, job);
`artifacts` is a JSONB blob {research_brief, questions, star_drafts}. RLS is
FORCEd with the SAME service-bypass clause as migration 0032, and the policy
name ends in `_user_isolation` so 0032's dynamic scan keeps covering it.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ISOLATION = (
    "(current_setting('app.bypass_rls'::text, true) = 'on' "
    "OR (current_setting('app.current_user_id'::text, true))::uuid = user_id)"
)


def upgrade() -> None:
    op.create_table(
        "interview_preps",
        sa.Column(
            "id",
            PgUUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            PgUUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            PgUUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifacts", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "generated_by", sa.Text(), nullable=False, server_default=sa.text("'grounded'")
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_interview_preps_user", "interview_preps", ["user_id"])
    op.create_unique_constraint(
        "uq_interview_preps_user_job", "interview_preps", ["user_id", "job_id"]
    )
    op.execute("ALTER TABLE interview_preps ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE interview_preps FORCE ROW LEVEL SECURITY")
    op.execute(
        'CREATE POLICY "interview_preps_user_isolation" ON interview_preps '
        f"USING ({_ISOLATION}) WITH CHECK ({_ISOLATION})"
    )


def downgrade() -> None:
    op.execute(
        'DROP POLICY IF EXISTS "interview_preps_user_isolation" ON interview_preps'
    )
    op.drop_table("interview_preps")
