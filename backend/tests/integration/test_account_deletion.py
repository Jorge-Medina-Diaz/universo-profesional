"""T1 — GDPR two-phase deletion: phase-1 cleanup is complete + phase-2 is scheduled.

Phase 1 (DELETE /me) must erase live secrets that the soft-delete's absent FK
cascade leaves behind — BYOK key + external connections — not just tokens.
Phase 2 (hard_delete_expired_accounts) must be wired into the worker cron and
actually purge past-retention soft-deleted accounts. A right-to-erasure that
silently no-ops is both a compliance breach and a silent-error-rule violation.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient


def test_hard_delete_is_scheduled() -> None:
    """The phase-2 hard-erase must be in the worker cron, not just registered."""
    from src.shared.worker import WorkerSettings

    cron_fns = {cj.coroutine.__name__ for cj in WorkerSettings.cron_jobs}
    assert "hard_delete_expired_accounts" in cron_fns, (
        "hard_delete_expired_accounts is registered as a function but NOT scheduled "
        "— soft-deleted accounts would never be erased."
    )


async def _register_login(client: AsyncClient, email: str) -> tuple[str, str]:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "S3cur3-Passw0rd!", "display_name": "Del", "locale": "es-ES"},
    )
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["user_id"]
    token = re.search(r"token=([\w-]+)", resp.json()["verification_link"]).group(1)  # type: ignore[union-attr]
    await client.post("/api/v1/auth/verify", json={"token": token})
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "S3cur3-Passw0rd!"}
    )
    assert resp.status_code == 200, resp.text
    return user_id, resp.json()["access_token"]


@pytest.mark.asyncio
async def test_delete_me_clears_byok_and_external_accounts(client: AsyncClient) -> None:
    from src.agents.infrastructure import byok
    from src.integrations.domain.external_account import ExternalAccount
    from src.integrations.infrastructure.repositories import SqlExternalAccountRepository
    from src.shared.db import with_user_session
    from src.shared.security import utc_now

    user_id, access = await _register_login(client, "erase-me@example.com")
    uid = UUID(user_id)

    # Seed a BYOK credential + a connected external account for this user.
    async with with_user_session(uid) as s:
        await byok.set_credential(s, user_id=uid, provider="anthropic", api_key="sk-secret")
        await SqlExternalAccountRepository(s).upsert(
            ExternalAccount.create(
                user_id=uid,
                provider="github",
                provider_user_id="42",
                provider_username="octocat",
                access_token="gho_live_token",
                refresh_token=None,
                expires_at=None,
                scopes=["repo"],
                metadata={},
                now=utc_now(),
            )
        )
    async with with_user_session(uid) as s:
        assert (await byok.get_credential_status(s, uid))[0] is True
        assert len(await SqlExternalAccountRepository(s).list_for_user(uid)) == 1

    # Phase 1: delete the account.
    resp = await client.delete("/api/v1/users/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200, resp.text

    # The live secrets must be gone (FK cascade does NOT fire on a soft-delete).
    async with with_user_session(uid) as s:
        assert (await byok.get_credential_status(s, uid))[0] is False
        assert await SqlExternalAccountRepository(s).list_for_user(uid) == []


@pytest.mark.asyncio
async def test_hard_delete_erases_past_retention_account(client: AsyncClient) -> None:
    from sqlalchemy import text
    from src.identity.infrastructure.tasks import hard_delete_expired_accounts
    from src.shared.db import get_session_factory

    user_id, _ = await _register_login(client, "old-soft-delete@example.com")

    # Soft-delete with a deleted_at older than the 30-day retention window.
    factory = get_session_factory()
    async with factory() as s:
        await s.execute(
            text("UPDATE users SET deleted_at = :ts WHERE id = :id"),
            {"ts": datetime.now(UTC) - timedelta(days=31), "id": user_id},
        )
        await s.commit()

    purged = await hard_delete_expired_accounts({})
    assert purged >= 1

    async with factory() as s:
        row = (
            await s.execute(text("SELECT 1 FROM users WHERE id = :id"), {"id": user_id})
        ).first()
    assert row is None, "past-retention soft-deleted account must be hard-erased"
