"""Add render_status to documents (visible render outcome).

Revision ID: 0033
Revises: 0032
Create Date: 2026-06-01

A failed/degraded CV render must be visible to the user (no-silent-errors).
The renderer falls back to writing an .html file when WeasyPrint fails;
render_status formalises that signal (ready | degraded | failed) end-to-end.
Existing rows are backfilled from the stored pdf_path suffix so history reads
truthfully instead of all defaulting to 'ready'.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "render_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'ready'"),
        ),
    )
    op.execute(
        "UPDATE documents SET render_status = 'degraded' "
        "WHERE pdf_path IS NOT NULL AND pdf_path LIKE '%.html'"
    )
    op.execute(
        "UPDATE documents SET render_status = 'failed' WHERE pdf_path IS NULL"
    )


def downgrade() -> None:
    op.drop_column("documents", "render_status")
