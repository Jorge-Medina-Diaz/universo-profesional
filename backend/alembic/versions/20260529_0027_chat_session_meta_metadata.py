"""Add metadata JSONB column to chat_session_meta.

Revision ID: 0027
Revises: 0026
Create Date: 2026-05-29

The sliding-window session digest previously created this column at runtime
via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` inside a live transaction, which
takes an AccessExclusiveLock and serialises all digest writes under concurrent
arq workers. The column is now declared here so the runtime DDL can be removed.
Uses IF NOT EXISTS so it is a no-op on databases where the old runtime path
already created the column.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE chat_session_meta ADD COLUMN IF NOT EXISTS metadata JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE chat_session_meta DROP COLUMN IF EXISTS metadata")
