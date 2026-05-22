"""Drop legacy relation columns/tables — Sprint R cutover.

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-15

⚠ **DESTRUCTIVE** ⚠ — this migration only runs after
`scripts/migrate_legacy_to_graph.py --apply` has been executed
against the same database and the operator has manually verified
(via the `graph_ingest_meta('legacy_migration_applied_at')` row)
that every relation now lives in the AGE personal graph.

Dropped artefacts:

  • Tables
      - evidences            (replaced by reified :Evidence nodes)
      - user_rubric_signals  (replaced by :Signal vertices)

  • Columns
      - artifacts.linked_skill_ids       (USES_TECH edges)
      - artifacts.linked_project_id      (PART_OF edges)
      - skills.evidence_refs             (DEMONSTRATES edges)
      - architecture_decisions.related_project_id   (PART_OF edges)
      - architecture_decisions.superseded_by        (SUPERSEDES edges)

The downgrade restores the *schema* but NOT the data — once the
graph is authoritative, rolling back is a code-only operation.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _safe_to_drop_legacy(connection: sa.engine.Connection) -> bool:
    """Only drop legacy relations when there's nothing to lose.

    Safe when EITHER:
      • the legacy → graph data migration was recorded (real cutover ran), OR
      • the database is fresh/empty (no users) — e.g. provisioning a new
        environment or the isolated test DB, where the legacy tables exist
        (created by 0001-0013) but hold no data.

    A populated DB without the marker is refused: that's a real database
    whose legacy data hasn't been migrated to the graph yet.
    """
    row = connection.execute(
        sa.text(
            "SELECT value FROM graph_ingest_meta "
            "WHERE name = 'legacy_migration_applied_at'"
        )
    ).first()
    if row is not None:
        return True
    user_count = connection.execute(
        sa.text("SELECT count(*) FROM users")
    ).scalar()
    return (user_count or 0) == 0


def upgrade() -> None:
    bind = op.get_bind()
    if not _safe_to_drop_legacy(bind):
        # Surface a clear error rather than silently dropping live data.
        msg = (
            "Migration 0017 refuses to run on a populated database because the "
            "legacy → graph data migration has not been recorded. Run "
            "`python -m scripts.migrate_legacy_to_graph --apply` first. "
            "(Fresh/empty databases with no users pass automatically.)"
        )
        raise RuntimeError(msg)

    # ------------------------------------------------------------------
    # Drop indexes that depend on the columns we're about to remove.
    # We use IF EXISTS guards so re-running after a partial apply is
    # idempotent.
    # ------------------------------------------------------------------
    op.execute("DROP INDEX IF EXISTS ix_evidences_skill")
    op.execute("DROP INDEX IF EXISTS ix_evidences_target")
    op.execute("DROP INDEX IF EXISTS ix_user_rubric_signals_user")
    op.execute("DROP INDEX IF EXISTS ix_user_rubric_signals_chunk")
    op.execute("DROP INDEX IF EXISTS ix_user_rubric_signals_status")

    # ------------------------------------------------------------------
    # Tables
    # ------------------------------------------------------------------
    op.execute("DROP POLICY IF EXISTS user_rubric_signals_rls ON user_rubric_signals")
    op.execute("DROP TABLE IF EXISTS user_rubric_signals CASCADE")

    op.execute("DROP POLICY IF EXISTS evidences_rls ON evidences")
    op.execute("DROP TABLE IF EXISTS evidences CASCADE")

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    op.drop_column("artifacts", "linked_skill_ids")
    op.drop_column("artifacts", "linked_project_id")
    op.drop_column("skills", "evidence_refs")
    op.drop_column("architecture_decisions", "related_project_id")
    op.drop_column("architecture_decisions", "superseded_by")


def downgrade() -> None:
    # The schema can be reconstructed, but the data is gone. We restore
    # the columns/tables with their original definitions so future
    # migrations stack cleanly; the operator can replay the dump if
    # they need the data back.
    op.add_column(
        "architecture_decisions",
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "architecture_decisions",
        sa.Column("related_project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "skills",
        sa.Column(
            "evidence_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "artifacts",
        sa.Column("linked_project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "artifacts",
        sa.Column(
            "linked_skill_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
    )

    # The two tables — recreated in their original Sprint G / Sprint 0003
    # shapes (modulo the indexes and policies, which we restore via raw
    # SQL because the original migrations use convenience helpers we
    # can't import from here without coupling).
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
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "skill_id",
            "evidence_entity_type",
            "evidence_entity_id",
            name="uq_evidences_triple",
        ),
    )
    op.create_index("ix_evidences_skill", "evidences", ["skill_id"])
    op.create_index(
        "ix_evidences_target",
        "evidences",
        ["evidence_entity_type", "evidence_entity_id"],
    )

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
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="'auto'"),
        sa.Column("last_reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "rubric_chunk_id", name="uq_signals_user_chunk"),
    )
