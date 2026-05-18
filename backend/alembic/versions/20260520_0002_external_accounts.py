"""External accounts + integration sync runs (GitHub, LinkedIn, …).

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-20
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),  # github, linkedin, gitlab, …
        sa.Column("provider_user_id", sa.Text(), nullable=True),
        sa.Column("provider_username", sa.Text(), nullable=True),
        sa.Column("access_token_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("refresh_token_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("connected_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("sync_status", sa.Text(), nullable=True),  # ok | pending | error
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.UniqueConstraint("user_id", "provider", name="uq_external_accounts_user_provider"),
    )
    op.create_index("ix_external_accounts_user", "external_accounts", ["user_id"])
    op.create_index("ix_external_accounts_provider", "external_accounts", ["provider"])
    op.execute("ALTER TABLE external_accounts ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY external_accounts_user_isolation ON external_accounts
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )

    op.create_table(
        "integration_sync_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("ok", sa.Boolean(), nullable=True),
        sa.Column("items_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("summary", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_integration_sync_runs_user_provider", "integration_sync_runs", ["user_id", "provider"])
    op.execute("ALTER TABLE integration_sync_runs ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY integration_sync_runs_user_isolation ON integration_sync_runs
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS integration_sync_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS external_accounts CASCADE")
