"""T2 — GDPR export/erase table coverage, enforced against the LIVE schema.

These guards fail when a future migration adds a user-scoped table without a
conscious GDPR decision — so personal data can never silently escape the Art.20
export or the Art.17 erase. They query information_schema, so they require the
AGE/pgvector test DB (the full migrated schema).
"""
from __future__ import annotations

import re

import pytest
from src.identity.infrastructure.exporter import (
    AI_ERASE_ACKNOWLEDGED,
    INTERNAL_NO_EXPORT,
    SECRET_BEARING,
    discover_ai_scoped_tables,
    discover_user_scoped_tables,
)
from src.shared.db import get_session_factory

# Column-name heuristic for "this looks like a secret we must never export".
# Anchored to real secret suffixes/terms so public ids (credential_id) and flags
# (mfa_enabled) are NOT false-positives, while password_hash / mfa_secret /
# share_token / *_encrypted / *_key secrets are.
_SECRET_COL = re.compile(
    r"_secret$|_token$|encrypted|_hash$|password|private_key|api_key"
)


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
async def test_every_ai_schema_user_table_is_erased() -> None:
    """The agno `ai` schema holds narrative memories + transcripts keyed by a
    user_id with NO FK to users, so the public-schema cascade never reaches it.

    The previous coverage guard only scanned `table_schema = 'public'`, so it
    was structurally blind to the `ai` schema — a permanent false green that let
    a deleted user's PII survive Art.17 erasure. The hard-delete now sweeps the
    ai schema dynamically; this asserts no ai user-table is unacknowledged.
    """
    factory = get_session_factory()
    async with factory() as s:
        ai_tables = await discover_ai_scoped_tables(s)
    unacknowledged = ai_tables - AI_ERASE_ACKNOWLEDGED
    assert not unacknowledged, (
        "ai-schema user-scoped tables not acknowledged for GDPR erase (add to "
        f"AI_ERASE_ACKNOWLEDGED after confirming the sweep covers them): {sorted(unacknowledged)}"
    )
