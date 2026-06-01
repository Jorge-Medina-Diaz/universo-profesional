"""Outbox projection substrate: seq on domain_events + cursor table (R4 slice 1).

Revision ID: 0038
Revises: 0037
Create Date: 2026-06-01

ADDITIVE — no write-path change. Reuses the existing `domain_events` table (rows
already written by activity_log) as the outbox substrate: a monotonic `seq` lets
a worker cursor-scan new events and project them durably (slice 1 = embeddings
reliability net). `outbox_projection_cursor` tracks per-projection progress.
Backfill assigns seq BEFORE wiring the DEFAULT so backfilled values and future
nextval() values never collide. No RLS on the new table (cross-user worker state,
same posture as domain_events).
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE domain_events ADD COLUMN IF NOT EXISTS seq bigint")
    # Backfill existing rows in occurred_at order, before the sequence is wired,
    # so historical values and future nextval() values can't collide.
    op.execute(
        """
        UPDATE domain_events d
        SET seq = s.rn
        FROM (
            SELECT event_id, row_number() OVER (ORDER BY occurred_at, event_id) AS rn
            FROM domain_events
        ) s
        WHERE d.event_id = s.event_id AND d.seq IS NULL
        """
    )
    op.execute("CREATE SEQUENCE IF NOT EXISTS domain_events_seq")
    op.execute(
        """
        DO $$
        DECLARE m bigint;
        BEGIN
            SELECT COALESCE(MAX(seq), 0) INTO m FROM domain_events;
            IF m > 0 THEN PERFORM setval('domain_events_seq', m, true); END IF;
        END $$
        """
    )
    op.execute(
        "ALTER TABLE domain_events ALTER COLUMN seq SET DEFAULT nextval('domain_events_seq')"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_domain_events_seq ON domain_events(seq)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS outbox_projection_cursor (
            projection_name text PRIMARY KEY,
            last_event_seq bigint NOT NULL DEFAULT 0,
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "INSERT INTO outbox_projection_cursor (projection_name) VALUES ('embeddings') "
        "ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS outbox_projection_cursor")
    op.execute("DROP INDEX IF EXISTS ix_domain_events_seq")
    op.execute("ALTER TABLE domain_events DROP COLUMN IF EXISTS seq")
    op.execute("DROP SEQUENCE IF EXISTS domain_events_seq")
