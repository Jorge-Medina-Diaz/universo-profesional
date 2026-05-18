"""Avatars, evidences, suggestions, reminders + last_reviewed_at on entities.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-20
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENTITIES_WITH_REVIEW = (
    "educations",
    "experiences",
    "projects",
    "skills",
    "certifications",
    "courses",
    "languages",
    "achievements",
    "interests",
)


def upgrade() -> None:
    # last_reviewed_at + source_metadata on every entity table
    for tbl in ENTITIES_WITH_REVIEW:
        op.add_column(
            tbl,
            sa.Column("last_reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        )
        op.add_column(
            tbl,
            sa.Column("source_metadata", postgresql.JSONB(), nullable=True),
        )

    # avatars
    op.create_table(
        "avatars",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # evidences (skill ↔ experience/project/achievement N:M with weight)
    op.create_table(
        "evidences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_entity_type", sa.Text(), nullable=False),  # experience, project, achievement, certification, course
        sa.Column("evidence_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("skill_id", "evidence_entity_type", "evidence_entity_id", name="uq_evidences_unique"),
    )
    op.create_index("ix_evidences_user", "evidences", ["user_id"])
    op.create_index("ix_evidences_skill", "evidences", ["skill_id"])
    op.execute("ALTER TABLE evidences ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY evidences_user_isolation ON evidences
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )

    # suggestions
    op.create_table(
        "suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),  # add_skill, update_role, expire_cert, apply_to_job (future)
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),  # rule_engine, llm, job_matcher (future)
        sa.Column("provider", sa.Text(), nullable=True),  # specific provider name
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),  # pending, accepted, rejected, expired
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("acted_on_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_suggestions_user_status", "suggestions", ["user_id", "status"])
    op.execute("ALTER TABLE suggestions ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY suggestions_user_isolation ON suggestions
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )

    # reminders (generic subject_type to reuse in future verticals)
    op.create_table(
        "reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),  # cert_expiring, course_stale, quarterly_review, application_followup (future)
        sa.Column("subject_type", sa.Text(), nullable=True),  # certification, course, application, interview (future)
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("due_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("recurrence", sa.Text(), nullable=True),  # null | quarterly | monthly | weekly
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("dispatched_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_reminders_user_due", "reminders", ["user_id", "due_at"])
    op.execute("ALTER TABLE reminders ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY reminders_user_isolation ON reminders
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )

    # import sessions (PDF flow: parse then commit selectively)
    op.create_table(
        "import_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),  # pdf, linkedin_zip, github
        sa.Column("status", sa.Text(), nullable=False, server_default="parsed"),  # parsed, partially_committed, committed, discarded
        sa.Column("parsed", postgresql.JSONB(), nullable=False),  # ParsedCv-shaped payload
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("committed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_import_sessions_user", "import_sessions", ["user_id"])
    op.execute("ALTER TABLE import_sessions ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY import_sessions_user_isolation ON import_sessions
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS import_sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS reminders CASCADE")
    op.execute("DROP TABLE IF EXISTS suggestions CASCADE")
    op.execute("DROP TABLE IF EXISTS evidences CASCADE")
    op.execute("DROP TABLE IF EXISTS avatars CASCADE")
    for tbl in ENTITIES_WITH_REVIEW:
        op.drop_column(tbl, "source_metadata")
        op.drop_column(tbl, "last_reviewed_at")
