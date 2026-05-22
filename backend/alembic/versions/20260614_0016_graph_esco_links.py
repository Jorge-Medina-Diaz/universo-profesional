"""graph_esco_links — bridge table between personal entities and ESCO.

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-14

Sprint cleanup: `coherence_v2._attach_esco_edge()` used to create this
table lazily at runtime via `CREATE TABLE IF NOT EXISTS`, an anti-pattern
(no RLS, no indexes, race on first write). We promote it to a proper
migration. The runtime `CREATE TABLE` is removed in the same change set.

The table records the (entity → ESCO concept) link that the entity
linker resolves. AGE cannot express cross-graph edges (personal graph →
ontology graph), so the link lives here keyed by the personal entity id
+ the ESCO IRI.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "graph_esco_links",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("esco_uri", sa.Text(), nullable=False),
        sa.Column("target_label", sa.Text(), nullable=False),
        sa.Column("score", sa.Numeric(4, 3), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint(
            "user_id", "entity_id", "esco_uri", name="pk_graph_esco_links"
        ),
    )
    # Reverse lookup: "who links to this ESCO concept?" — used by the
    # cross-type dedup query in coherence_v2.find_by_esco_uri().
    op.create_index(
        "ix_graph_esco_links_uri",
        "graph_esco_links",
        ["user_id", "esco_uri"],
    )
    op.execute("ALTER TABLE graph_esco_links ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY graph_esco_links_rls ON graph_esco_links
            USING (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS graph_esco_links_rls ON graph_esco_links")
    op.drop_index("ix_graph_esco_links_uri", table_name="graph_esco_links")
    op.drop_table("graph_esco_links")
