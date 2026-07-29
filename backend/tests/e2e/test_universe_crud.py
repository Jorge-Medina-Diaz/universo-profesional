"""E2E test: create a user then CRUD all universe entity types."""
from __future__ import annotations

import re

import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str = "jorge@webtools.es") -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "S3cur3-Passw0rd!", "locale": "es-ES"},
    )
    assert resp.status_code == 201, resp.text
    token = re.search(r"token=([\w-]+)", resp.json()["verification_link"]).group(1)  # type: ignore[union-attr]
    await client.post("/api/v1/auth/verify", json={"token": token})
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "S3cur3-Passw0rd!"}
    )
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_generate_cv(client: AsyncClient) -> None:
    access = await _register_and_login(client)
    h = {"Authorization": f"Bearer {access}"}

    # Seed minimal universe
    await client.post(
        "/api/v1/universe/experience",
        json={
            "organization": "Acme",
            "role": "Senior Python Engineer",
            "description": "FastAPI backend, PostgreSQL, Docker",
            "highlights": ["3x throughput improvement"],
            "competences": ["Python", "FastAPI", "PostgreSQL"],
        },
        headers=h,
    )
    await client.post(
        "/api/v1/universe/skill",
        json={"name": "Python", "category": "hard", "level": "expert"},
        headers=h,
    )

    # Generate CV
    r = await client.post(
        "/api/v1/documents/generate-cv",
        json={
            "job_description": "Senior Python developer with FastAPI and PostgreSQL experience",
            "template": "ats-classic",
            "language": "es",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["document_id"]
    assert body["json_resume"]["work"]
