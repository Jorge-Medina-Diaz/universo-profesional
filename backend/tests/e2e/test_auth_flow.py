"""E2E test: register → verify → login → fetch /me."""
from __future__ import annotations

import re

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_verify_login_me(client: AsyncClient) -> None:
    # Register
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "jorge@webtools.es",
            "password": "S3cur3-Passw0rd!",
            "display_name": "Jorge",
            "locale": "es-ES",
        },
    )
    assert resp.status_code == 201, resp.text
    payload = resp.json()
    link = payload["verification_link"]
    token = re.search(r"token=([\w-]+)", link).group(1)  # type: ignore[union-attr]

    # Verify
    resp = await client.post("/api/v1/auth/verify", json={"token": token})
    assert resp.status_code == 200, resp.text

    # Login
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "jorge@webtools.es", "password": "S3cur3-Passw0rd!"},
    )
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    assert tokens["access_token"]

    # /me
    resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200, resp.text
    me = resp.json()
    assert me["email"] == "jorge@webtools.es"
    assert me["email_verified"] is True
