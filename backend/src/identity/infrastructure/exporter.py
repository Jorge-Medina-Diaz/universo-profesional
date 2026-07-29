"""RGPD Art. 20 exporter — dumps every row owned by the user.

The set of user-scoped tables is DISCOVERED dynamically from information_schema
(every public base table with a `user_id` column, plus `users` itself), so a new
migration that adds a user table is included automatically — it can never
silently fall out of the export. Two curated lists shape that set:

  * INTERNAL_NO_EXPORT — user-scoped tables deliberately excluded (secrets,
    operational/billing telemetry, the internal event store + audit logs, and
    large derived/system artifacts that are regenerated from exported entities).
  * _REDACT_COLUMNS — per-table columns stripped from an otherwise-exported row
    (the table is user content, but the column is a secret).

The GDPR Art.17 erase counterpart is the FK `ON DELETE CASCADE` from `users`
(see hard_delete_expired_accounts); MANUAL_ERASE lists the user-scoped tables
that lack that cascade and must be deleted explicitly.

tests/integration/test_gdpr_table_coverage.py asserts, against the live schema,
that every user-scoped table is either exported or denied, that no secret-bearing
table is exported, and that every user-scoped table is erased (cascade OR
MANUAL_ERASE).
"""
from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.identity.application.ports import UserDataExporter

logger = structlog.get_logger(__name__)

# User-scoped tables NOT included in the Art.20 portability export.
INTERNAL_NO_EXPORT: frozenset[str] = frozenset(
    {
        # Secrets — exporting these would leak live credentials.
        "refresh_tokens",
        "email_tokens",
        "oauth_tokens",
        "oauth_authorization_codes",
        "oauth_clients",
        "user_llm_credentials",
        "external_accounts",
        # Operational / billing telemetry — not personal data the user provided.
        "llm_usage_logs",
        "mcp_invocations",
        "quota_usage",
        "integration_sync_runs",
        # Internal event store + audit logs (PII erased via MANUAL_ERASE / cascade).
        "domain_events",
        "universe_change_log",
        "graph_edge_audit",
        # Large derived/system artifacts — regenerated from the exported entities.
        "graph_entity_embeddings",
        "graph_esco_links",
        "knowledge_chunks",
        "avatars",
    }
)

# Subset of INTERNAL_NO_EXPORT whose rows carry credentials/secrets. The CI guard
# asserts these are ALWAYS denied, so the dynamic export can never leak them even
# if a future table is added.
SECRET_BEARING: frozenset[str] = frozenset(
    {
        "refresh_tokens",
        "email_tokens",
        "oauth_tokens",
        "oauth_authorization_codes",
        "oauth_clients",
        "user_llm_credentials",
        "external_accounts",
    }
)

# User-scoped tables with NO `ON DELETE CASCADE` FK to users — the phase-2
# hard-erase must delete these explicitly (the cascade won't reach them).
MANUAL_ERASE: frozenset[str] = frozenset({"domain_events"})

# agno-managed `ai`-schema tables we have consciously confirmed are erased by
# the dynamic ai-schema sweep in hard_delete_expired_accounts. The GDPR
# coverage test fails if the live `ai` schema grows a user-scoped table not
# listed here, forcing a human to confirm it's covered (fail-until-classified,
# the same contract the public-schema erase guard uses).
AI_ERASE_ACKNOWLEDGED: frozenset[str] = frozenset(
    {"agno_memories", "agno_sessions"}
)

# Per-table secret columns stripped from an exported row (the table is user
# content we keep, but these specific columns are secrets).
_REDACT_COLUMNS: dict[str, frozenset[str]] = {
    "users": frozenset({"password_hash", "mfa_secret"}),
    "documents": frozenset({"share_token"}),
}


async def discover_user_scoped_tables(session: AsyncSession) -> set[str]:
    """Every public base table that has a `user_id` column.

    `users` itself is keyed by `id`, not `user_id`, so it is added separately by
    callers that need the full owned-data set.
    """
    rows = (
        await session.execute(
            text(
                "SELECT c.table_name FROM information_schema.columns c "
                "JOIN information_schema.tables t "
                "  ON t.table_name = c.table_name AND t.table_schema = c.table_schema "
                "WHERE c.table_schema = 'public' AND c.column_name = 'user_id' "
                "  AND t.table_type = 'BASE TABLE'"
            )
        )
    ).all()
    return {r[0] for r in rows}


async def discover_ai_scoped_tables(session: AsyncSession) -> set[str]:
    """agno-managed tables in the `ai` schema that carry a `user_id` column
    (agno_memories = narrative PII facts, agno_sessions = full chat transcripts).

    These are created by the agno framework, NOT our migrations: `user_id` is a
    plain string with NO foreign key to `public.users`, so the GDPR cascade from
    `DELETE FROM users` never reaches them. They must be erased explicitly. The
    GDPR coverage test asserts every one of these is in AI_ERASE so a future
    agno table can never silently survive a right-to-erasure.
    """
    rows = (
        await session.execute(
            text(
                "SELECT c.table_name FROM information_schema.columns c "
                "JOIN information_schema.tables t "
                "  ON t.table_name = c.table_name AND t.table_schema = c.table_schema "
                "WHERE c.table_schema = 'ai' AND c.column_name = 'user_id' "
                "  AND t.table_type = 'BASE TABLE'"
            )
        )
    ).all()
    return {r[0] for r in rows}


class SqlUserDataExporter(UserDataExporter):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # The owning column is `user_id` on every table except `users`, where it's
    # the primary key `id`.
    _TABLE_USER_COL: ClassVar[dict[str, str]] = {"users": "id"}

    async def export_all(self, user_id: UUID) -> dict[str, Any]:
        # Dynamic: everything the user owns, minus the curated exclusions. A new
        # user-scoped table is exported automatically (never silently dropped).
        tables = ({"users"} | await discover_user_scoped_tables(self._session)) - INTERNAL_NO_EXPORT
        out: dict[str, Any] = {"user_id": str(user_id), "tables": {}}
        errors: list[str] = []
        for table in sorted(tables):
            col = self._TABLE_USER_COL.get(table, "user_id")
            redact = _REDACT_COLUMNS.get(table, frozenset())
            # Table name comes from information_schema, never user input.
            stmt = text(f"SELECT row_to_json(t) AS row FROM {table} t WHERE {col} = :uid")
            try:
                rows = (await self._session.execute(stmt, {"uid": str(user_id)})).all()
                records = [r[0] for r in rows]
                if redact:
                    for rec in records:
                        if isinstance(rec, dict):
                            for key in redact:
                                rec.pop(key, None)
                out["tables"][table] = records
            except Exception as exc:
                # A failed table must NOT silently vanish from an Art.20 export
                # presented as complete. Log loudly (-> Sentry) AND surface it in
                # the export payload so the data subject sees the gap. Keep the
                # shape a list so consumers don't break on a dict.
                logger.error("gdpr_export_table_failed", table=table, error=str(exc))
                out["tables"][table] = []
                errors.append(table)
        if errors:
            out["errors"] = errors
        return out
