"""Canonical RLS policies: NULLIF-safe user match + bypass arm everywhere.

Revision ID: 0039
Revises: 0038
Create Date: 2026-06-09

Running the app as the RLS-subject role (cvs_app) surfaced two latent policy
defects that the owner/superuser connection had been masking:

1. ``current_setting('app.current_user_id', true)::uuid`` explodes with
   ``invalid input syntax for type uuid: ""`` when the GUC is defined-empty
   (e.g. a pooled connection where ``RESET app.current_user_id`` ran — RESET
   *defines* an unset custom GUC as ''). SQL ``OR`` does not short-circuit,
   so even the service-bypass arm didn't protect the cast. Fix: wrap with
   ``NULLIF(…, '')`` so '' behaves exactly like unset (NULL = user_id → no
   rows, default-deny preserved).

2. Migration 0032 rewrote only the ``*_user_isolation``-named policies. Six
   tables created with ``*_rls``-named policies (community_summaries,
   entity_quarantine, graph_edge_audit, graph_entity_embeddings,
   graph_esco_links, llm_usage_logs) kept the plain single-arm form: no
   service-bypass arm (background workers scanning cross-user silently get
   zero rows) and no FORCE (decorative for the owner).

This migration rewrites EVERY policy in schema public whose qual references
``app.current_user_id`` to the one canonical clause and FORCEs RLS on its
table. Discovery is catalog-driven so future policies created with either
naming convention are covered on a fresh-DB run too.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CANONICAL = (
    "(current_setting('app.bypass_rls'::text, true) = 'on' "
    "OR NULLIF(current_setting('app.current_user_id'::text, true), '')::uuid = user_id)"
)
# Pre-0039 forms, for downgrade fidelity.
_BYPASS_NO_NULLIF = (
    "(current_setting('app.bypass_rls'::text, true) = 'on' "
    "OR (current_setting('app.current_user_id'::text, true))::uuid = user_id)"
)
_PLAIN = "(user_id = (current_setting('app.current_user_id'::text, true))::uuid)"


def _user_policies(conn) -> list[tuple[str, str]]:  # type: ignore[no-untyped-def]
    rows = conn.execute(
        text(
            "SELECT c.relname, p.polname "
            "FROM pg_policy p "
            "JOIN pg_class c ON c.oid = p.polrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' "
            "AND pg_get_expr(p.polqual, p.polrelid) LIKE '%app.current_user_id%' "
            "ORDER BY c.relname"
        )
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def _recreate(table: str, policy: str, clause: str, force: bool) -> None:
    op.execute(f'DROP POLICY IF EXISTS "{policy}" ON {table}')
    op.execute(
        f'CREATE POLICY "{policy}" ON {table} USING ({clause}) WITH CHECK ({clause})'
    )
    op.execute(
        f"ALTER TABLE {table} {'FORCE' if force else 'NO FORCE'} ROW LEVEL SECURITY"
    )


def upgrade() -> None:
    conn = op.get_bind()
    for table, policy in _user_policies(conn):
        _recreate(table, policy, _CANONICAL, force=True)


def downgrade() -> None:
    conn = op.get_bind()
    for table, policy in _user_policies(conn):
        legacy_plain = policy.endswith("_rls")
        _recreate(
            table,
            policy,
            _PLAIN if legacy_plain else _BYPASS_NO_NULLIF,
            force=not legacy_plain,
        )
