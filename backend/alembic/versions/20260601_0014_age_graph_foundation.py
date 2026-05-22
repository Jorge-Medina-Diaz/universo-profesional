"""AGE graph foundation — extension, two graphs, metadata, quarantine tables.

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-01

Sprint M of the Universo Profesional v2 plan. Establishes the graph
backbone: Apache AGE extension, the `universe_personal` and
`universe_ontology` graphs, plus the small relational sidecars we need
for the rest of the sprint:

  • `graph_ingest_meta`  — release version of the ESCO corpus we last
    loaded (so the ingest script is idempotent across redeploys).
  • `entity_quarantine`  — Sprint N populates this when a node can't be
    auto-linked to ESCO with high enough confidence; declared now so
    the FK from coherence_v2 can already exist by then.
  • `graph_entity_embeddings` — sidecar table holding the canonical
    embedding for every personal :Entity, indexed via HNSW. Lets us do
    pgvector cosine queries that mix tenant scoping with the graph
    without packing 1536 floats into agtype properties.

The graphs themselves are created inside a DO block so the migration is
idempotent — `create_graph()` raises if the graph already exists, which
would otherwise break `alembic upgrade` on a database that already has
them from `docker/postgres-init.sql`.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. AGE extension + graphs (idempotent)
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS age")
    op.execute("LOAD 'age'")
    # CRITICAL: keep `public` FIRST so the CREATE TABLE statements below
    # land in `public`, not `ag_catalog`. AGE's create_graph() and the
    # cypher() function are reachable via the explicit `ag_catalog.`
    # prefix when needed; for clarity we also keep `ag_catalog` on the
    # path so bare `cypher(...)` calls in this migration resolve.
    op.execute(
        "SELECT set_config('search_path', 'public,ag_catalog,\"$user\"', false)"
    )

    # `create_graph` has no IF NOT EXISTS; pre-check ag_graph instead of
    # trying-and-catching since AGE raises `InvalidSchemaName` (3F000) and
    # PL/pgSQL exception handlers don't always intercept it cleanly when
    # the rollback also retracts the savepoint.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM ag_catalog.ag_graph WHERE name = 'universe_personal') THEN
                PERFORM create_graph('universe_personal');
            END IF;
        END
        $$
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM ag_catalog.ag_graph WHERE name = 'universe_ontology') THEN
                PERFORM create_graph('universe_ontology');
            END IF;
        END
        $$
        """
    )

    # ------------------------------------------------------------------
    # 2. Ingest metadata — used by scripts/ingest_esco.py
    # ------------------------------------------------------------------
    op.create_table(
        "graph_ingest_meta",
        sa.Column("name", sa.String(64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ------------------------------------------------------------------
    # 3. entity_quarantine — Sprint N populates this when the ESCO linker
    #    returns SUGGESTED (low-confidence) or when outlier detection
    #    flags a new node.
    # ------------------------------------------------------------------
    op.create_table(
        "entity_quarantine",
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
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        # 'esco_low_confidence' | 'outlier' | 'cross_type_conflict'
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column(
            "candidates",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resolution", sa.String(128), nullable=True),
    )
    op.create_index(
        "ix_entity_quarantine_user_pending",
        "entity_quarantine",
        ["user_id", "resolved_at"],
        postgresql_where=sa.text("resolved_at IS NULL"),
    )
    op.create_index(
        "ix_entity_quarantine_entity",
        "entity_quarantine",
        ["entity_id"],
    )
    op.execute("ALTER TABLE entity_quarantine ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY entity_quarantine_rls ON entity_quarantine
            USING (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )

    # ------------------------------------------------------------------
    # 4. graph_entity_embeddings — sidecar HNSW index over personal
    #    :Entity vertex embeddings, scoped per user via RLS.
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "graph_entity_embeddings",
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # The embedding column is declared as float[] above so Alembic can
    # describe it; convert to pgvector(1536) here to enable HNSW.
    op.execute(
        "ALTER TABLE graph_entity_embeddings "
        "ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)"
    )
    op.create_index(
        "ix_graph_entity_embeddings_user",
        "graph_entity_embeddings",
        ["user_id", "kind"],
    )
    op.execute(
        "CREATE INDEX ix_graph_entity_embeddings_hnsw "
        "ON graph_entity_embeddings USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute("ALTER TABLE graph_entity_embeddings ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY graph_entity_embeddings_rls ON graph_entity_embeddings
            USING (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )

    # ------------------------------------------------------------------
    # 5. ontology_embeddings — pgvector side table holding the canonical
    #    multilingual embedding for every ESCO concept (Occupation /
    #    EscoSkill / ISCOGroup). AGE's agtype properties don't index
    #    vectors efficiently, so this table is the entity-linker's
    #    primary input.
    # ------------------------------------------------------------------
    op.create_table(
        "ontology_embeddings",
        sa.Column("uri", sa.Text(), primary_key=True),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        "ALTER TABLE ontology_embeddings "
        "ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)"
    )
    op.create_index(
        "ix_ontology_embeddings_label",
        "ontology_embeddings",
        ["label"],
    )
    op.execute(
        "CREATE INDEX ix_ontology_embeddings_hnsw "
        "ON ontology_embeddings USING hnsw (embedding vector_cosine_ops)"
    )

    # ------------------------------------------------------------------
    # 6. graph_edge_audit — temporal audit log for graph edges. AGE
    #    edges themselves carry valid_from/valid_to, but cross-process
    #    consumers (curator, retrieval invalidation) read this table
    #    rather than running Cypher in a tight loop.
    # ------------------------------------------------------------------
    op.create_table(
        "graph_edge_audit",
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
        sa.Column("edge_type", sa.String(64), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        # 'create' | 'update' | 'expire' | 'revive'
        sa.Column("op", sa.String(16), nullable=False),
        sa.Column(
            "occurred_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index(
        "ix_graph_edge_audit_user_time",
        "graph_edge_audit",
        ["user_id", "occurred_at"],
    )
    op.execute("ALTER TABLE graph_edge_audit ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY graph_edge_audit_rls ON graph_edge_audit
            USING (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ontology_embeddings_hnsw")
    op.drop_index("ix_ontology_embeddings_label", table_name="ontology_embeddings")
    op.drop_table("ontology_embeddings")

    op.execute("DROP POLICY IF EXISTS graph_edge_audit_rls ON graph_edge_audit")
    op.drop_index("ix_graph_edge_audit_user_time", table_name="graph_edge_audit")
    op.drop_table("graph_edge_audit")

    op.execute(
        "DROP POLICY IF EXISTS graph_entity_embeddings_rls ON graph_entity_embeddings"
    )
    op.execute("DROP INDEX IF EXISTS ix_graph_entity_embeddings_hnsw")
    op.drop_index(
        "ix_graph_entity_embeddings_user", table_name="graph_entity_embeddings"
    )
    op.drop_table("graph_entity_embeddings")

    op.execute("DROP POLICY IF EXISTS entity_quarantine_rls ON entity_quarantine")
    op.drop_index("ix_entity_quarantine_entity", table_name="entity_quarantine")
    op.drop_index("ix_entity_quarantine_user_pending", table_name="entity_quarantine")
    op.drop_table("entity_quarantine")

    op.drop_table("graph_ingest_meta")

    # We intentionally do NOT drop the AGE graphs in downgrade. Dropping
    # them would destroy every user's personal graph; downgrades should
    # be reserved for staging environments and the operator is expected
    # to manage the AGE artefacts manually if needed.
