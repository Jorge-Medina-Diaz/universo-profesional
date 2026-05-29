"""Typed graph vertex labels (Sprint R).

Revision ID: 0024
Revises: 0023
Create Date: 2026-05-26

Creates the typed vertex labels in the AGE `universe_personal` graph so
that new entity writes use :Experience, :Skill, … instead of the generic
:Entity label.  Legacy :Entity nodes remain readable via label-less MATCH
patterns.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TYPED_LABELS = [
    "Experience",
    "Education",
    "Skill",
    "Project",
    "Certification",
    "Course",
    "Language",
    "Achievement",
    "Interest",
    "Artifact",
    "ArchitectureDecision",
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS age")
    op.execute("LOAD 'age'")
    op.execute("SELECT set_config('search_path', 'public,ag_catalog,\"$user\"', false)")

    for label in _TYPED_LABELS:
        op.execute(
            f"""
            DO $$
            BEGIN
                PERFORM create_vlabel('universe_personal', '{label}');
            EXCEPTION WHEN OTHERS THEN
                -- vlabel may already exist; idempotent
                NULL;
            END $$;
            """
        )


def downgrade() -> None:
    op.execute("LOAD 'age'")
    op.execute("SELECT set_config('search_path', 'public,ag_catalog,\"$user\"', false)")

    for label in _TYPED_LABELS:
        op.execute(
            f"""
            DO $$
            BEGIN
                PERFORM drop_vlabel('universe_personal', '{label}');
            EXCEPTION WHEN OTHERS THEN
                NULL;
            END $$;
            """
        )
