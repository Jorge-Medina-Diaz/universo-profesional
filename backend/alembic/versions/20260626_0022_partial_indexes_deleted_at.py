"""Partial indexes on deleted_at IS NULL.

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-26

Adds partial indexes covering the most frequent filter pattern:
  user_id = X AND deleted_at IS NULL

This avoids seq-scans when repositories list active entities.
Tables affected: educations, experiences, projects, skills, certifications,
courses, languages, achievements, interests, artifacts, skill_stacks,
architecture_decisions, user_rubric_signals.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = [
    "educations",
    "experiences",
    "projects",
    "skills",
    "certifications",
    "courses",
    "languages",
    "achievements",
    "interests",
    "artifacts",
    "skill_stacks",
    "architecture_decisions",
    "user_rubric_signals",
]


def upgrade() -> None:
    for table in _TABLES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_user_active "
            f"ON {table}(user_id) WHERE deleted_at IS NULL"
        )


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_user_active")
