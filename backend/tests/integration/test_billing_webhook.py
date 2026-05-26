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
async def test_mock_checkout_upgrades_plan(client: AsyncClient) -> None:
    access = await _register_and_login(client, "billing@example.com")
    h = {"Authorization": f"Bearer {access}"}

    # Initial plan is free
    r = await client.get("/api/v1/billing/subscription", headers=h)
    assert r.status_code == 200
    assert r.json()["plan"] == "free"

    # Simulate Stripe checkout completion via mock webhook
    me = await client.get("/api/v1/users/me", headers=h)
    user_id = me.json()["user_id"]

    r = await client.post(
        "/api/v1/billing/webhook/test",
        json={"event": "checkout.completed", "user_id": user_id, "plan": "premium"},
    )
    assert r.status_code == 200
    assert r.json()["plan"] == "premium"

    # Subscription reflects upgrade
    r = await client.get("/api/v1/billing/subscription", headers=h)
    assert r.status_code == 200
    assert r.json()["plan"] == "premium"


@pytest.mark.asyncio
async def test_mock_cancel_downgrades_plan(client: AsyncClient) -> None:
    access = await _register_and_login(client, "billing2@example.com")
    h = {"Authorization": f"Bearer {access}"}

    me = await client.get("/api/v1/users/me", headers=h)
    user_id = me.json()["user_id"]

    # Upgrade first
    await client.post(
        "/api/v1/billing/webhook/test",
        json={"event": "checkout.completed", "user_id": user_id, "plan": "pro"},
    )

    # Cancel
    r = await client.post(
        "/api/v1/billing/webhook/test",
        json={"event": "subscription.canceled", "user_id": user_id},
    )
    assert r.status_code == 200
    assert r.json()["plan"] == "free"
    assert r.json()["status"] == "canceled"


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
