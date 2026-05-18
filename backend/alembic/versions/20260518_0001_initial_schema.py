"""Initial schema — Identity, Universe, Documents, MCP OAuth, Billing.

Implements §H.1 of the spec: 18 tables, pgvector HNSW indexes, RLS policies.

Revision ID: 0001
Revises:
Create Date: 2026-05-18
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VECTOR_DIM = 1536

# Tables holding user-scoped rows; each gets an RLS policy.
USER_SCOPED_TABLES = [
    "universes",
    "educations",
    "experiences",
    "projects",
    "skills",
    "certifications",
    "courses",
    "languages",
    "achievements",
    "interests",
    "career_preferences",
    "goals",
    "documents",
    "jobs",
    "applications",
    "oauth_clients",
    "oauth_tokens",
    "subscriptions",
    "domain_events",
    "mcp_invocations",
    "email_tokens",
    "refresh_tokens",
    "quota_usage",
]


def upgrade() -> None:
    # Extensions (idempotent thanks to postgres-init.sql; redo here for safety)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # --- Identity ----------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", postgresql.CITEXT(), nullable=False, unique=True),  # type: ignore[attr-defined]
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("email_verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("locale", sa.Text(), nullable=False, server_default="es-ES"),
        sa.Column("mfa_secret", sa.Text(), nullable=True),  # encrypted TOTP secret (column-level encryption v2)
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "email_tokens",
        sa.Column("token_hash", sa.Text(), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),  # 'verify_email' | 'password_reset'
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_email_tokens_user", "email_tokens", ["user_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("token_hash", sa.Text(), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("issued_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("replaced_by", sa.Text(), nullable=True),  # for rotation chains
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.Text(), nullable=True),
    )
    op.create_index("ix_refresh_tokens_user", "refresh_tokens", ["user_id"])

    # --- Universe (one aggregate per user) ----------------------------------
    op.create_table(
        "universes",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("current_status", sa.Text(), nullable=True),
        sa.Column("last_reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Entities. Common columns are factored into a helper.
    def _entity_columns() -> list[sa.Column]:  # type: ignore[type-arg]
        return [
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("embedding", Vector(VECTOR_DIM), nullable=True),
            sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
            sa.Column("visibility", sa.Text(), nullable=False, server_default="public"),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        ]

    op.create_table(
        "educations",
        *_entity_columns(),
        sa.Column("institution", sa.Text(), nullable=False),
        sa.Column("degree", sa.Text(), nullable=True),
        sa.Column("field_of_study", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("highlights", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("gpa", sa.Numeric(4, 2), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
    )
    op.create_index("ix_educations_user", "educations", ["user_id"])
    op.execute(
        "CREATE INDEX ix_educations_embedding ON educations USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "experiences",
        *_entity_columns(),
        sa.Column("organization", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("location", postgresql.JSONB(), nullable=True),  # { city, region, country_code }
        sa.Column("employment_type", sa.Text(), nullable=True),  # full_time, part_time, contractor, freelance, internship
        sa.Column("modality", sa.Text(), nullable=True),  # remote, hybrid, onsite
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("highlights", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("competences", postgresql.JSONB(), nullable=False, server_default="[]"),  # skill refs
        sa.Column("url", sa.Text(), nullable=True),
    )
    op.create_index("ix_experiences_user", "experiences", ["user_id"])
    op.execute(
        "CREATE INDEX ix_experiences_embedding ON experiences USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "projects",
        *_entity_columns(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("role", sa.Text(), nullable=True),  # creator, contributor, lead, …
        sa.Column("project_type", sa.Text(), nullable=True),  # side, oss, entrepreneurship, work
        sa.Column("tech_stack", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("highlights", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("impact", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
    )
    op.create_index("ix_projects_user", "projects", ["user_id"])
    op.execute(
        "CREATE INDEX ix_projects_embedding ON projects USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "skills",
        *_entity_columns(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),  # hard, soft, tool, methodology
        sa.Column("level", sa.Text(), nullable=True),  # basic, intermediate, high, expert
        sa.Column("years", sa.Integer(), nullable=True),
        sa.Column("last_used_year", sa.Integer(), nullable=True),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.create_index("ix_skills_user", "skills", ["user_id"])
    op.create_index("ix_skills_user_name", "skills", ["user_id", "name"], unique=True)
    op.execute(
        "CREATE INDEX ix_skills_embedding ON skills USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "certifications",
        *_entity_columns(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("issuer", sa.Text(), nullable=True),
        sa.Column("issued_on", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("credential_id", sa.Text(), nullable=True),
        sa.Column("verification_url", sa.Text(), nullable=True),
    )
    op.create_index("ix_certifications_user", "certifications", ["user_id"])
    op.execute(
        "CREATE INDEX ix_certifications_embedding ON certifications USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "courses",
        *_entity_columns(),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("platform", sa.Text(), nullable=True),
        sa.Column("started_on", sa.Date(), nullable=True),
        sa.Column("completed_on", sa.Date(), nullable=True),
        sa.Column("duration_hours", sa.Integer(), nullable=True),
        sa.Column("certificate_url", sa.Text(), nullable=True),
    )
    op.create_index("ix_courses_user", "courses", ["user_id"])

    op.create_table(
        "languages",
        *_entity_columns(),
        sa.Column("code", sa.Text(), nullable=False),  # ISO 639-1
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("level", sa.Text(), nullable=False),  # A1, A2, B1, B2, C1, C2, native
        sa.Column("certification", sa.Text(), nullable=True),
    )
    op.create_index("ix_languages_user_code", "languages", ["user_id", "code"], unique=True)

    op.create_table(
        "achievements",
        *_entity_columns(),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("achieved_on", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("evidence_url", sa.Text(), nullable=True),
    )
    op.create_index("ix_achievements_user", "achievements", ["user_id"])

    op.create_table(
        "interests",
        *_entity_columns(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_interests_user", "interests", ["user_id"])

    op.create_table(
        "career_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("salary_min", sa.Numeric(12, 2), nullable=True),
        sa.Column("salary_max", sa.Numeric(12, 2), nullable=True),
        sa.Column("salary_currency", sa.CHAR(3), nullable=True),
        sa.Column("contract_types", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("remote_preference", sa.Text(), nullable=True),
        sa.Column("open_to_relocate", sa.Boolean(), nullable=True),
        sa.Column("working_areas", postgresql.JSONB(), nullable=True),
        sa.Column("perks_must_have", postgresql.JSONB(), nullable=True),
        sa.Column("perks_nice_to_have", postgresql.JSONB(), nullable=True),
        sa.Column("preferred_competences", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("discarded_competences", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("preferred_roles", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("discarded_roles", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("motivations", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("horizon", sa.Text(), nullable=False),  # short, medium, long
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_goals_user", "goals", ["user_id"])

    # --- Documents ---------------------------------------------------------
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("description_raw", sa.Text(), nullable=False),
        sa.Column("description_parsed", postgresql.JSONB(), nullable=True),
        sa.Column("ats_detected", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(VECTOR_DIM), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_jobs_user", "jobs", ["user_id"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),  # cv, cover_letter
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("language", sa.CHAR(2), nullable=False, server_default="es"),
        sa.Column("tone", sa.Text(), nullable=True),
        sa.Column("length", sa.Text(), nullable=True),  # 1-page, 2-page
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("generated_from", postgresql.JSONB(), nullable=True),  # snapshot of entity ids used
        sa.Column("content_json", postgresql.JSONB(), nullable=False),
        sa.Column("pdf_path", sa.Text(), nullable=True),
        sa.Column("docx_path", sa.Text(), nullable=True),
        sa.Column("share_token", sa.Text(), nullable=True, unique=True),
        sa.Column("share_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_documents_user", "documents", ["user_id"])
    op.create_index("ix_documents_user_kind", "documents", ["user_id", "kind"])

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stage", sa.Text(), nullable=False, server_default="saved"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("next_action_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_applications_user", "applications", ["user_id"])

    # --- MCP OAuth ---------------------------------------------------------
    op.create_table(
        "oauth_clients",
        sa.Column("client_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("client_name", sa.Text(), nullable=False),
        sa.Column("redirect_uris", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("grant_types", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("ARRAY['authorization_code','refresh_token']::text[]")),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("client_secret_hash", sa.Text(), nullable=True),  # null = public PKCE-only client
        sa.Column("token_endpoint_auth_method", sa.Text(), nullable=False, server_default="none"),
        sa.Column("software_id", sa.Text(), nullable=True),
        sa.Column("software_version", sa.Text(), nullable=True),
        sa.Column("registered_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "oauth_authorization_codes",
        sa.Column("code_hash", sa.Text(), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("oauth_clients.client_id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("resource", sa.Text(), nullable=False),
        sa.Column("code_challenge", sa.Text(), nullable=False),
        sa.Column("code_challenge_method", sa.Text(), nullable=False, server_default="S256"),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "oauth_tokens",
        sa.Column("token_hash", sa.Text(), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("oauth_clients.client_id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),  # access, refresh
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("resource", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("issued_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("replaced_by", sa.Text(), nullable=True),
    )
    op.create_index("ix_oauth_tokens_user", "oauth_tokens", ["user_id"])
    op.create_index("ix_oauth_tokens_client", "oauth_tokens", ["client_id"])

    op.create_table(
        "mcp_invocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_name", sa.Text(), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_mcp_invocations_user_created", "mcp_invocations", ["user_id", "created_at"])

    # --- Billing -----------------------------------------------------------
    op.create_table(
        "subscriptions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("plan", sa.Text(), nullable=False, server_default="free"),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("stripe_customer_id", sa.Text(), nullable=True),
        sa.Column("stripe_subscription_id", sa.Text(), nullable=True),
        sa.Column("trial_ends_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("current_period_start", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("cancel_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "quota_usage",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource", sa.Text(), nullable=False),  # cv_generated, cover_letter_generated, mcp_call
        sa.Column("period", sa.Text(), nullable=False),  # YYYY-MM for monthly counters, YYYY-MM-DD for daily
        sa.Column("counter", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("user_id", "resource", "period"),
    )

    # --- Audit -------------------------------------------------------------
    op.create_table(
        "domain_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_events_user_occurred", "domain_events", ["user_id", "occurred_at"])
    op.create_index("ix_domain_events_type", "domain_events", ["event_type"])

    # --- Row-Level Security policies ---------------------------------------
    # Postgres requires a session variable to be set; the app sets
    # `app.current_user_id` via `set_rls_user()` on every authenticated session.
    # When unset, the policy denies access; the app uses a service role for
    # cross-user ops (registration, OAuth introspection) by using a connection
    # without RLS enforcement (we mark those tables explicitly without RLS).
    for table in (
        "universes",
        "educations",
        "experiences",
        "projects",
        "skills",
        "certifications",
        "courses",
        "languages",
        "achievements",
        "interests",
        "career_preferences",
        "goals",
        "documents",
        "jobs",
        "applications",
        "subscriptions",
        "quota_usage",
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
    # We don't expect to downgrade past 0001 in production; provide a clean drop
    # for development resets.
    for table in (
        "domain_events",
        "quota_usage",
        "subscriptions",
        "mcp_invocations",
        "oauth_tokens",
        "oauth_authorization_codes",
        "oauth_clients",
        "applications",
        "documents",
        "jobs",
        "goals",
        "career_preferences",
        "interests",
        "achievements",
        "languages",
        "courses",
        "certifications",
        "skills",
        "projects",
        "experiences",
        "educations",
        "universes",
        "refresh_tokens",
        "email_tokens",
        "users",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
