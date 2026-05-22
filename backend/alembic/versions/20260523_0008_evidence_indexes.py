"""Reverse-lookup index on evidences (target entity → skills).

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-23

The existing 0003 migration created indexes on (user_id) and (skill_id).
Both miss the "what skills do I have for this project?" direction, which the
coherence engine and CV generation hit often. This adds the composite reverse
index. No data changes.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_evidences_target",
        "evidences",
        ["user_id", "evidence_entity_type", "evidence_entity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_evidences_target", table_name="evidences")
