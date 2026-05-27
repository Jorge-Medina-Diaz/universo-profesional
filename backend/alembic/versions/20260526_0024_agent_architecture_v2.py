"""Agent Architecture v2: Knowledge namespaces + Structured Memory.

Revision ID: 0024
Revises: 0023
Create Date: 2026-05-26

1. Adds `namespace` to knowledge_documents / knowledge_chunks so the same
   substrate can hold universe docs, job descriptions, recruiter profiles,
   social connections, and learned patterns.
2. Creates structured memory tables for semantic, procedural and episodic
   tiers — these complement Agno's native memory with domain-specific
   schemas that the context providers read directly.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Knowledge namespaces
    # ------------------------------------------------------------------
    op.add_column(
        "knowledge_documents",
        sa.Column(
            "namespace",
            sa.Text(),
            nullable=False,
            server_default="universe",
        ),
    )
    op.create_index(
        "ix_knowledge_documents_ns",
        "knowledge_documents",
        ["user_id", "namespace", "created_at"],
    )

    op.add_column(
        "knowledge_chunks",
        sa.Column(
            "namespace",
            sa.Text(),
            nullable=False,
            server_default="universe",
        ),
    )
    op.create_index(
        "ix_knowledge_chunks_ns",
        "knowledge_chunks",
        ["user_id", "namespace"],
    )

    # ------------------------------------------------------------------
    # 2. Structured Memory — Semantic (facts about the user)
    # ------------------------------------------------------------------
    op.create_table(
        "user_semantic_memory",
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
        sa.Column("category", sa.Text(), nullable=False),
        # e.g. 'preference', 'fact', 'goal', 'skill_gap', 'industry_target'
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("source", sa.Text(), nullable=False, server_default="agent_inference"),
        # 'agent_chat', 'user_explicit', 'import', 'inferred'
        sa.Column("last_confirmed_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
    )
    op.create_index(
        "ix_semantic_memory_user_cat",
        "user_semantic_memory",
        ["user_id", "category", "key"],
    )

    # ------------------------------------------------------------------
    # 3. Structured Memory — Procedural (learned rules / preferences)
    # ------------------------------------------------------------------
    op.create_table(
        "user_procedural_memory",
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
        sa.Column("scope", sa.Text(), nullable=False),
        # e.g. 'cv_generation', 'quiz_formulation', 'job_search', 'universe_updates'
        sa.Column("trigger_pattern", sa.Text(), nullable=False),
        # human-readable or regex-like pattern that activates this rule
        sa.Column("action_rule", sa.Text(), nullable=False),
        # what the agent should DO when trigger matches
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
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
    )
    op.create_index(
        "ix_procedural_memory_user_scope",
        "user_procedural_memory",
        ["user_id", "scope", "active"],
    )

    # ------------------------------------------------------------------
    # 4. Structured Memory — Episodic (session summaries with extracted entities)
    # ------------------------------------------------------------------
    op.create_table(
        "session_episodes",
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
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("extracted_facts", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("open_questions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("decisions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("mentioned_entities", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("mood", sa.Text(), nullable=True),
        # 'frustrated', 'satisfied', 'curious', 'urgent'
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_session_episodes_user_session",
        "session_episodes",
        ["user_id", "session_id"],
    )
    op.create_index(
        "ix_session_episodes_user_created",
        "session_episodes",
        ["user_id", "created_at"],
    )

    # ------------------------------------------------------------------
    # 5. RLS policies
    # ------------------------------------------------------------------
    for table in (
        "user_semantic_memory",
        "user_procedural_memory",
        "session_episodes",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_user_isolation ON {table}
            USING (user_id = current_setting('app.current_user_id', true)::uuid)
            WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
            """
        )


def downgrade() -> None:
    for table in ("user_semantic_memory", "user_procedural_memory", "session_episodes"):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    op.drop_index("ix_knowledge_chunks_ns", table_name="knowledge_chunks")
    op.drop_column("knowledge_chunks", "namespace")
    op.drop_index("ix_knowledge_documents_ns", table_name="knowledge_documents")
    op.drop_column("knowledge_documents", "namespace")
