"""polyglot foundation — area_strengths + artifact + skill_stack + extensions.

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-26

Adds the foundation for representing polyglot software profiles:
  - `area_strengths`: per-user × per-area depth/breadth/recency/confidence
    (computed by `shape_service`; the source of truth for T/π/M-shape
    detection).
  - `artifact`: GitHub repos, talks, blog posts, OSS contribs, papers,
    podcasts, videos — first-class citizens, linked to projects/skills.
  - `skill_stack`: nameable cluster of related skills ("JVM backend",
    "AWS data platform").
  - Extensions to existing tables:
      • universes.primary_area + secondary_areas (cached shape result)
      • projects.domain_tags (industry tags: fintech, healthtech, …)
      • experiences.industry_sector + seniority_level

The corpus rubrics (0010) stay global; these are user-scoped with RLS.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- area_strengths ----------------------------------------------------
    op.create_table(
        "area_strengths",
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
        sa.Column("area", sa.Text(), nullable=False),
        sa.Column("depth_years", sa.Numeric(4, 1), nullable=False, server_default="0"),
        sa.Column("breadth_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recency_months", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False, server_default="0"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "area", name="uq_area_strengths_user_area"),
    )
    op.create_index("ix_area_strengths_user", "area_strengths", ["user_id"])
    op.execute(
        "CREATE INDEX ix_area_strengths_primary ON area_strengths(user_id) "
        "WHERE is_primary = TRUE"
    )

    # --- artifact ----------------------------------------------------------
    op.create_table(
        "artifacts",
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
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("venue", sa.Text(), nullable=True),
        sa.Column(
            "linked_skill_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "linked_project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("metrics", postgresql.JSONB(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("visibility", sa.Text(), nullable=False, server_default="public"),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("source_metadata", postgresql.JSONB(), nullable=True),
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
    )
    op.create_index("ix_artifacts_user_type", "artifacts", ["user_id", "type"])
    op.execute(
        "CREATE INDEX ix_artifacts_linked_project ON artifacts(linked_project_id) "
        "WHERE linked_project_id IS NOT NULL"
    )
    op.execute("CREATE INDEX ix_artifacts_linked_skills ON artifacts USING GIN(linked_skill_ids)")

    # --- skill_stack -------------------------------------------------------
    op.create_table(
        "skill_stacks",
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
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("area", sa.Text(), nullable=False),
        sa.Column(
            "skill_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("user_id", "slug", name="uq_skill_stacks_user_slug"),
    )
    op.create_index("ix_skill_stacks_user_area", "skill_stacks", ["user_id", "area"])

    # --- extender entidades existentes -------------------------------------
    op.add_column(
        "projects",
        sa.Column(
            "domain_tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.execute("CREATE INDEX ix_projects_domain_tags ON projects USING GIN(domain_tags)")

    op.add_column("experiences", sa.Column("industry_sector", sa.Text(), nullable=True))
    op.add_column("experiences", sa.Column("seniority_level", sa.Text(), nullable=True))

    op.add_column("universes", sa.Column("primary_area", sa.Text(), nullable=True))
    op.add_column(
        "universes",
        sa.Column(
            "secondary_areas",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )

    # --- RLS ---------------------------------------------------------------
    for table in ("area_strengths", "artifacts", "skill_stacks"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_user_isolation ON {table}
            USING (user_id = current_setting('app.current_user_id', true)::uuid)
            WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
            """
        )


def downgrade() -> None:
    for table in ("area_strengths", "artifacts", "skill_stacks"):
        op.execute(f"DROP POLICY IF EXISTS {table}_user_isolation ON {table}")
    op.drop_column("universes", "secondary_areas")
    op.drop_column("universes", "primary_area")
    op.drop_column("experiences", "seniority_level")
    op.drop_column("experiences", "industry_sector")
    op.execute("DROP INDEX IF EXISTS ix_projects_domain_tags")
    op.drop_column("projects", "domain_tags")
    op.drop_table("skill_stacks")
    op.drop_table("artifacts")
    op.drop_table("area_strengths")
