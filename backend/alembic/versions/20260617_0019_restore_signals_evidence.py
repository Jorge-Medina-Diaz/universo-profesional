"""Restore user_rubric_signals + evidences tables — undo premature 0017 drop.

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-17

Migration 0017 ("drop_legacy_relations") dropped ``user_rubric_signals`` and
``evidences`` as part of a planned cutover to AGE ``:Signal``/``:Evidence``
vertices — but the application code was never ported: ``signal_extraction.py``,
``SqlAlchemyUserRubricSignalRepository`` and the ORM classes
``UserRubricSignalOrm`` / ``EvidenceOrm`` still read and write these SQL tables.
The result was ``relation "user_rubric_signals" does not exist`` on every
coherence upsert (caught as a warning) and a broken signals/coverage + evidence
feature.

This migration recreates both tables with their original schemas (mirroring
0012 for signals and 0003 for evidences), including indexes and per-user RLS
policies, so the feature works again. The tables come back empty;
``recompute_user_signals()`` regenerates signals from the user's entities. The
graph-native port remains a future refinement.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text("SELECT to_regclass(:n)"), {"n": f"public.{name}"}
        ).scalar()
    )


def upgrade() -> None:
    # Idempotent guards: only create what 0017 actually dropped. (A fresh DB
    # provisioned after this migration will already have these via 0017's
    # refusal-to-run path, so guard each.)
    if not _table_exists("evidences"):
        op.create_table(
            "evidences",
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
                "skill_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("skills.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("evidence_entity_type", sa.Text(), nullable=False),
            sa.Column("evidence_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "skill_id",
                "evidence_entity_type",
                "evidence_entity_id",
                name="uq_evidences_unique",
            ),
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

    if not _table_exists("user_rubric_signals"):
        op.create_table(
            "user_rubric_signals",
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
                "rubric_chunk_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("rubric_chunks.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("section_kind", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("confidence", sa.Numeric(3, 2), nullable=False, server_default="0"),
            sa.Column("evidence_entity_type", sa.Text(), nullable=True),
            sa.Column(
                "evidence_entity_ids",
                postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
                nullable=False,
                server_default="{}",
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("source", sa.Text(), nullable=False, server_default="auto"),
            sa.Column("last_reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "user_id", "rubric_chunk_id", name="uq_user_rubric_signals_user_chunk"
            ),
        )
        op.create_index("ix_user_rubric_signals_user", "user_rubric_signals", ["user_id"])
        op.create_index(
            "ix_user_rubric_signals_chunk", "user_rubric_signals", ["rubric_chunk_id"]
        )
        op.create_index(
            "ix_user_rubric_signals_status",
            "user_rubric_signals",
            ["user_id", "status"],
        )
        op.execute("ALTER TABLE user_rubric_signals ENABLE ROW LEVEL SECURITY")
        op.execute(
            """
            CREATE POLICY user_rubric_signals_user_isolation ON user_rubric_signals
            USING (user_id = current_setting('app.current_user_id', true)::uuid)
            WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
            """
        )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS user_rubric_signals_user_isolation ON user_rubric_signals"
    )
    op.execute("DROP TABLE IF EXISTS user_rubric_signals CASCADE")
    op.execute("DROP POLICY IF EXISTS evidences_user_isolation ON evidences")
    op.execute("DROP TABLE IF EXISTS evidences CASCADE")
