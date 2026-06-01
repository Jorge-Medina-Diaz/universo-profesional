"""T2 — GDPR export/erase table coverage, enforced against the LIVE schema.

These guards fail when a future migration adds a user-scoped table without a
conscious GDPR decision — so personal data can never silently escape the Art.20
export or the Art.17 erase. They query information_schema, so they require the
AGE/pgvector test DB (the full migrated schema).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from src.identity.infrastructure.exporter import (
    INTERNAL_NO_EXPORT,
    MANUAL_ERASE,
    SECRET_BEARING,
    discover_user_scoped_tables,
)
from src.shared.db import get_session_factory


@pytest.mark.asyncio
async def test_every_user_scoped_table_is_classified() -> None:
    """Each user-scoped table is either exported (dynamically) or explicitly denied."""
    factory = get_session_factory()
    async with factory() as s:
        discovered = await discover_user_scoped_tables(s)
    # The export set is `discovered - INTERNAL_NO_EXPORT`; nothing is "missing".
    # We still assert the DENY list has no stale entries (typo / dropped table),
    # so the exclusions stay meaningful.
    stale = INTERNAL_NO_EXPORT - discovered
    assert not stale, f"INTERNAL_NO_EXPORT names tables that no longer exist (stale): {sorted(stale)}"
    assert discovered, "discovery found no user-scoped tables — query/schema problem"


@pytest.mark.asyncio
async def test_no_secret_bearing_table_is_exported() -> None:
    """Tables carrying credentials/secrets must always be denied from the export."""
    factory = get_session_factory()
    async with factory() as s:
        discovered = await discover_user_scoped_tables(s)
    leaked = (SECRET_BEARING & discovered) - INTERNAL_NO_EXPORT
    assert not leaked, f"secret-bearing tables would be exported: {sorted(leaked)}"


@pytest.mark.asyncio
async def test_every_user_scoped_table_is_erased_on_account_delete() -> None:
    """Every user-scoped table either cascades from users.id OR is in MANUAL_ERASE.

    Otherwise a hard-delete would leave that table's PII behind (Art.17 breach).
    """
    factory = get_session_factory()
    async with factory() as s:
        discovered = await discover_user_scoped_tables(s)
        cascading = {
            r[0]
            for r in (
                await s.execute(
                    text(
                        "SELECT kcu.table_name "
                        "FROM information_schema.referential_constraints rc "
                        "JOIN information_schema.key_column_usage kcu "
                        "  ON rc.constraint_name = kcu.constraint_name "
                        " AND rc.constraint_schema = kcu.table_schema "
                        "JOIN information_schema.constraint_column_usage ccu "
                        "  ON rc.unique_constraint_name = ccu.constraint_name "
                        "WHERE rc.delete_rule = 'CASCADE' AND kcu.column_name = 'user_id' "
                        "  AND ccu.table_name = 'users'"
                    )
                )
            ).all()
        }
    not_erased = discovered - cascading - MANUAL_ERASE
    assert not not_erased, (
        "user-scoped tables that would survive a hard-delete (no CASCADE FK to "
        f"users, not in MANUAL_ERASE): {sorted(not_erased)}"
    )
