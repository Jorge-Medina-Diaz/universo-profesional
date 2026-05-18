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
async def test_universe_summary_and_crud(client: AsyncClient) -> None:
    access = await _register_and_login(client)
    h = {"Authorization": f"Bearer {access}"}

    # Empty summary
    r = await client.get("/api/v1/universe/summary", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["counts"]["educations"] == 0
    assert body["counts"]["experiences"] == 0

    # Add education
    r = await client.post(
        "/api/v1/universe/education",
        json={"institution": "UCM", "degree": "Licenciado", "field_of_study": "CS"},
        headers=h,
    )
    assert r.status_code == 201
    edu_id = r.json()["id"]

    # Add experience
    r = await client.post(
        "/api/v1/universe/experience",
        json={
            "organization": "Acme",
            "role": "Backend Engineer",
            "description": "Worked on the API",
            "highlights": ["3x throughput"],
        },
        headers=h,
    )
    assert r.status_code == 201

    # Add skill
    r = await client.post(
        "/api/v1/universe/skill",
        json={"name": "Python", "category": "hard", "level": "expert"},
        headers=h,
    )
    assert r.status_code == 201

    # Patch education
    r = await client.patch(
        f"/api/v1/universe/education/{edu_id}",
        json={"degree": "Ingeniero"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["degree"] == "Ingeniero"

    # Summary should now reflect everything
    r = await client.get("/api/v1/universe/summary", headers=h)
    counts = r.json()["counts"]
    assert counts["educations"] == 1
    assert counts["experiences"] == 1
    assert counts["skills"] == 1


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
