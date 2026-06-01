"""FORCE row-level security with a service-role bypass flag.

Revision ID: 0032
Revises: 0031
Create Date: 2026-06-01

The app connects to Postgres as the table OWNER, and owners bypass RLS unless
FORCE ROW LEVEL SECURITY is set — so the per-table *_user_isolation policies
were effectively decorative (a forgotten `WHERE user_id` in app code leaked
cross-tenant data with nothing to stop it).

This migration:
  1. Rewrites every `<table>_user_isolation` policy to also pass when
     `app.bypass_rls = 'on'` (the trusted-service escape hatch — set only by
     `set_rls_user(session, None)` for background workers that scan across
     users: curator, reminders cron, hard-delete). Default-deny is preserved:
     an unset flag yields `NULL = 'on'` → falls through to the user_id check.
  2. FORCEs RLS on each of those tables, so enforcement now applies to the
     owner connection too.

All policies were verified byte-identical before this change
(`current_user_id::uuid = user_id` for both USING and WITH CHECK), so the
rewrite is mechanical. Fully reversible (downgrade restores the plain policy
and clears FORCE).
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PLAIN = "(current_setting('app.current_user_id'::text, true))::uuid = user_id"
_WITH_BYPASS = (
    "(current_setting('app.bypass_rls'::text, true) = 'on' "
    "OR (current_setting('app.current_user_id'::text, true))::uuid = user_id)"
)


def _isolation_tables(conn) -> list[str]:  # type: ignore[no-untyped-def]
    rows = conn.execute(
        text(
            "SELECT tablename FROM pg_policies "
            "WHERE schemaname = 'public' AND policyname LIKE '%\\_user\\_isolation' "
            "ORDER BY tablename"
        )
    ).fetchall()
    return [r[0] for r in rows]


def _recreate(conn, table: str, clause: str, force: bool) -> None:  # type: ignore[no-untyped-def]
    policy = f"{table}_user_isolation"
    op.execute(f'DROP POLICY IF EXISTS "{policy}" ON {table}')
    op.execute(
        f'CREATE POLICY "{policy}" ON {table} '
        f"USING ({clause}) WITH CHECK ({clause})"
    )
    op.execute(
        f"ALTER TABLE {table} "
        f"{'FORCE' if force else 'NO FORCE'} ROW LEVEL SECURITY"
    )


def upgrade() -> None:
    conn = op.get_bind()
    for table in _isolation_tables(conn):
        _recreate(conn, table, _WITH_BYPASS, force=True)


def downgrade() -> None:
    conn = op.get_bind()
    for table in _isolation_tables(conn):
        _recreate(conn, table, _PLAIN, force=False)
