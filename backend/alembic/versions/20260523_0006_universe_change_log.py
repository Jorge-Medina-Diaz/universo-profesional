"""universe_change_log (append-only trajectory).

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-23

The current snapshot lives in universe.{table}; this is the immutable history
of every field-level change. Used by the curator (detect oscillation, recent
activity), by CV generation ("currently learning" section), and by chat HITL
cards ("you said 5 years two weeks ago — bump to 6?"). Append-only by design:
no UPDATEs or DELETEs at the application layer.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "universe_change_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("change_type", sa.Text(), nullable=False),
        sa.Column("field", sa.Text(), nullable=True),
        sa.Column("old_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("agent_run_id", sa.Text(), nullable=True),
        sa.Column(
            "changed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_universe_change_log_entity",
        "universe_change_log",
        ["user_id", "entity_type", "entity_id", "changed_at"],
        postgresql_using="btree",
    )
    op.create_index(
        "ix_universe_change_log_user_time",
        "universe_change_log",
        ["user_id", "changed_at"],
    )
    op.create_check_constraint(
        "ck_universe_change_log_change_type",
        "universe_change_log",
        "change_type IN ('create', 'update', 'delete', 'merge')",
    )
    op.execute("ALTER TABLE universe_change_log ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY universe_change_log_user_isolation ON universe_change_log
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS universe_change_log CASCADE")
