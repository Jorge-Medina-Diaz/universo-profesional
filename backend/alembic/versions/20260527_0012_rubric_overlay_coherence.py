"""user_rubric_signals — overlay personal sobre el corpus de rúbricas globales.

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-27

Cierra el bucle fractal: rúbricas (corpus global) ↔ universo (datos personales)
ahora tienen una arista explícita en `user_rubric_signals`. Cada fila indica
que un usuario "posee / practica / aspira a / debe evitar / podría enseñar"
un signal concreto de una rúbrica concreta, con la evidencia que lo sustenta
(skill_id / project_id / experience_id / artifact_id / …).

Esta tabla es el insumo para:
  - `signal_extraction_service` (auto-cobertura por embedding match)
  - `tech_radar_specialist` (narración signals por área primaria)
  - `portfolio_specialist` (gap vs JD requiere signals concretos)
  - `curator` (mark stale 180+ días sin revisar)

También añade `last_reviewed_at` a `artifacts` (faltaba en 0011 — el ORM ya
lo declaraba pero la columna no estaba en la migración).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
        # semantics
        sa.Column("section_kind", sa.Text(), nullable=False),  # criteria|questions|signals|anti_patterns|resources
        sa.Column("status", sa.Text(), nullable=False),  # aspire|practice|own|teach|avoid
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False, server_default="0"),
        # evidence
        sa.Column("evidence_entity_type", sa.Text(), nullable=True),
        sa.Column(
            "evidence_entity_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
        # metadata
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
    op.create_index(
        "ix_user_rubric_signals_user", "user_rubric_signals", ["user_id"]
    )
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
    op.drop_table("user_rubric_signals")
