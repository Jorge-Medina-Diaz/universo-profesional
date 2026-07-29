"""Integration tests: billing webhook with mock Stripe provider."""
from __future__ import annotations

import re

import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "S3cur3-Passw0rd!", "locale": "es-ES"},
    )
    assert resp.status_code == 201
    link = resp.json()["verification_link"]
    token = re.search(r"token=([\w-]+)", link).group(1)  # type: ignore[union-attr]
    await client.post("/api/v1/auth/verify", json={"token": token})
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "S3cur3-Passw0rd!"},
    )
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_real_webhook_rejects_mock_provider(client: AsyncClient) -> None:
    """The real /webhook endpoint must refuse when stripe_provider != real."""
    r = await client.post(
        "/api/v1/billing/webhook",
        headers={"stripe-signature": "test"},
        content=b'{"type":"checkout.session.completed"}',
    )
    assert r.status_code == 400
    assert "webhook not configured" in r.text.lower() or "not configured" in r.text.lower()
