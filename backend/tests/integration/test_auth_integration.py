"""Integration tests: complete auth flow (register → verify → login → refresh)."""
from __future__ import annotations

import re

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_verify_login_refresh_flow(client: AsyncClient) -> None:
    """End-to-end auth lifecycle with real database."""
    # 1) Register
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "authflow@test.local",
            "password": "S3cur3-Passw0rd!",
            "display_name": "Auth Flow",
            "locale": "es-ES",
        },
    )
    assert resp.status_code == 201, resp.text
    payload = resp.json()
    assert payload["user_id"]
    assert payload["email"] == "authflow@test.local"
    link = payload["verification_link"]
    token = re.search(r"token=([\w-]+)", link).group(1)  # type: ignore[union-attr]

    # 2) Verify email
    resp = await client.post("/api/v1/auth/verify", json={"token": token})
    assert resp.status_code == 200, resp.text

    # 3) Login
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "authflow@test.local", "password": "S3cur3-Passw0rd!"},
    )
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["user_id"] == payload["user_id"]

    # 4) Refresh
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 200, resp.text
    refreshed = resp.json()
    assert refreshed["access_token"]
    assert refreshed["refresh_token"] != tokens["refresh_token"]
    assert refreshed["user_id"] == payload["user_id"]

    # 5) Access protected resource
    resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {refreshed['access_token']}"},
    )
    assert resp.status_code == 200
    me = resp.json()
    assert me["email_verified"] is True


@pytest.mark.asyncio
async def test_login_fails_before_verification(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "unverified@test.local",
            "password": "S3cur3-Passw0rd!",
            "locale": "es-ES",
        },
    )
    assert resp.status_code == 201

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "unverified@test.local", "password": "S3cur3-Passw0rd!"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_revoked_token_fails(client: AsyncClient) -> None:
    # Register + verify + login
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "revoke@test.local",
            "password": "S3cur3-Passw0rd!",
            "locale": "es-ES",
        },
    )
    link = resp.json()["verification_link"]
    token = re.search(r"token=([\w-]+)", link).group(1)  # type: ignore[union-attr]
    await client.post("/api/v1/auth/verify", json={"token": token})

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "revoke@test.local", "password": "S3cur3-Passw0rd!"},
    )
    refresh_token = login.json()["refresh_token"]

    # Refresh once (rotates the token)
    r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r1.status_code == 200

    # Re-use old token should fail
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r2.status_code == 401
