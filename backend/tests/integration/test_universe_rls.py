"""Integration tests: Universe CRUD with Row-Level Security (user isolation)."""
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
async def test_user_cannot_read_another_users_entities(client: AsyncClient) -> None:
    alice_token = await _register_and_login(client, "alice@example.com")
    bob_token = await _register_and_login(client, "bob@example.com")

    # Alice creates an education
    h_alice = {"Authorization": f"Bearer {alice_token}"}
    r = await client.post(
        "/api/v1/universe/education",
        json={"institution": "MIT", "degree": "BSc", "field_of_study": "CS"},
        headers=h_alice,
    )
    assert r.status_code == 201
    edu_id = r.json()["id"]

    # Bob tries to patch it
    h_bob = {"Authorization": f"Bearer {bob_token}"}
    r = await client.patch(
        f"/api/v1/universe/education/{edu_id}",
        json={"degree": "PhD"},
        headers=h_bob,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_cannot_delete_another_users_entities(client: AsyncClient) -> None:
    alice_token = await _register_and_login(client, "alice2@example.com")
    bob_token = await _register_and_login(client, "bob2@example.com")

    h_alice = {"Authorization": f"Bearer {alice_token}"}
    r = await client.post(
        "/api/v1/universe/skill",
        json={"name": "Python", "category": "hard", "level": "expert"},
        headers=h_alice,
    )
    assert r.status_code == 201
    skill_id = r.json()["id"]

    h_bob = {"Authorization": f"Bearer {bob_token}"}
    r = await client.delete(f"/api/v1/universe/skill/{skill_id}", headers=h_bob)
    assert r.status_code == 404

    # Alice can still see it
    r = await client.get(f"/api/v1/universe/skill/{skill_id}", headers=h_alice)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_summary_is_isolated_per_user(client: AsyncClient) -> None:
    alice_token = await _register_and_login(client, "alice3@example.com")
    bob_token = await _register_and_login(client, "bob3@example.com")

    h_alice = {"Authorization": f"Bearer {alice_token}"}
    await client.post(
        "/api/v1/universe/experience",
        json={
            "organization": "Acme",
            "role": "Dev",
            "description": "Backend",
            "highlights": ["ship"],
        },
        headers=h_alice,
    )

    h_bob = {"Authorization": f"Bearer {bob_token}"}
    r = await client.get("/api/v1/universe/summary", headers=h_bob)
    assert r.status_code == 200
    assert r.json()["counts"]["experiences"] == 0

    r = await client.get("/api/v1/universe/summary", headers=h_alice)
    assert r.status_code == 200
    assert r.json()["counts"]["experiences"] == 1
