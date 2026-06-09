"""Integration tests for FORCE-RLS tenant isolation + service bypass (R2).

These assert the DB itself enforces per-user isolation (defense-in-depth), not
just application-layer WHERE clauses — the whole point of FORCE ROW LEVEL
SECURITY. Requires a real Postgres (migration 0032 applied).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from src.shared.db import with_user_session

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# A representative user-scoped, RLS-protected table.
_TABLE = "notes"


async def _create_user(user_id: uuid.UUID) -> None:
    """Seed a bare users row (service scope) so notes.user_id's FK holds.

    Under the owner/superuser the FK target could be skipped silently; under
    cvs_app the policy also hides foreign users, so the seed must run in the
    trusted service scope.
    """
    async with with_user_session(None) as s:
        await s.execute(
            text("INSERT INTO users (id, email) VALUES (:id, :email)"),
            {"id": str(user_id), "email": f"rls-{user_id}@test.local"},
        )


async def _insert_note(user_id: uuid.UUID, body: str) -> uuid.UUID:
    await _create_user(user_id)
    note_id = uuid.uuid4()
    async with with_user_session(user_id) as s:
        await s.execute(
            text(
                "INSERT INTO notes (id, user_id, body_md, tags, created_at, updated_at) "
                "VALUES (:id, :uid, :body, '{}', now(), now())"
            ),
            {"id": str(note_id), "uid": str(user_id), "body": body},
        )
    return note_id


async def test_force_rls_blocks_cross_tenant_reads() -> None:
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    note_a = await _insert_note(user_a, "a-secret")

    # A sees own row
    async with with_user_session(user_a) as s:
        seen = (
            await s.execute(text("SELECT count(*) FROM notes WHERE id = :id"), {"id": str(note_a)})
        ).scalar()
        assert seen == 1

    # B must NOT see A's row even with an explicit id query (DB-enforced)
    async with with_user_session(user_b) as s:
        seen = (
            await s.execute(text("SELECT count(*) FROM notes WHERE id = :id"), {"id": str(note_a)})
        ).scalar()
        assert seen == 0, "FORCE RLS isolation breach: B can read A's row"


async def test_force_rls_blocks_cross_tenant_update_and_delete() -> None:
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    note_a = await _insert_note(user_a, "a-immutable-by-b")

    # B's UPDATE/DELETE affect zero rows (RLS hides them from B entirely)
    async with with_user_session(user_b) as s:
        res = await s.execute(
            text("UPDATE notes SET body_md = 'hacked' WHERE id = :id"), {"id": str(note_a)}
        )
        assert res.rowcount == 0
        res = await s.execute(text("DELETE FROM notes WHERE id = :id"), {"id": str(note_a)})
        assert res.rowcount == 0

    # A's row is intact
    async with with_user_session(user_a) as s:
        body = (
            await s.execute(text("SELECT body_md FROM notes WHERE id = :id"), {"id": str(note_a)})
        ).scalar()
        assert body == "a-immutable-by-b"


async def test_service_bypass_reads_across_users() -> None:
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    await _insert_note(user_a, "svc-a")
    await _insert_note(user_b, "svc-b")

    # None-scope = trusted service: bypass ON → sees both users' rows.
    async with with_user_session(None) as s:
        distinct = (
            await s.execute(
                text("SELECT count(DISTINCT user_id) FROM notes WHERE user_id IN (:a, :b)"),
                {"a": str(user_a), "b": str(user_b)},
            )
        ).scalar()
        assert distinct == 2


async def test_unset_user_sees_nothing() -> None:
    # A random/never-inserted user id sees zero rows (default-deny holds).
    async with with_user_session(uuid.uuid4()) as s:
        n = (await s.execute(text("SELECT count(*) FROM notes"))).scalar()
        assert n == 0
