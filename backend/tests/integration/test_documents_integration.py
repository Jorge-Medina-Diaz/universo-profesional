"""Integration tests: document generation with mock LLM."""
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
async def test_generate_cv_with_mock_llm(client: AsyncClient) -> None:
    access = await _register_and_login(client, "docs@test.local")
    h = {"Authorization": f"Bearer {access}"}

    # Seed universe
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
    assert body["json_resume"]
    assert body["pdf_url"] or body["docx_url"]

    # List documents
    r = await client.get("/api/v1/documents", headers=h)
    assert r.status_code == 200
    docs = r.json()
    assert len(docs) == 1
    assert docs[0]["kind"] == "cv"

    # Get single document
    doc_id = body["document_id"]
    r = await client.get(f"/api/v1/documents/{doc_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["id"] == doc_id


@pytest.mark.asyncio
async def test_generate_cover_letter_with_mock_llm(client: AsyncClient) -> None:
    access = await _register_and_login(client, "cover@test.local")
    h = {"Authorization": f"Bearer {access}"}

    r = await client.post(
        "/api/v1/documents/generate-cv",
        json={
            "job_description": "Looking for a backend engineer",
            "template": "ats-classic",
            "language": "en",
            "kind": "cover_letter",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["document_id"]
    assert body["json_resume"]


@pytest.mark.asyncio
async def test_document_rls(client: AsyncClient) -> None:
    alice = await _register_and_login(client, "alice_doc@test.local")
    bob = await _register_and_login(client, "bob_doc@test.local")

    h_alice = {"Authorization": f"Bearer {alice}"}
    r = await client.post(
        "/api/v1/documents/generate-cv",
        json={"job_description": "JD", "template": "ats-classic", "language": "es"},
        headers=h_alice,
    )
    assert r.status_code == 201
    doc_id = r.json()["document_id"]

    h_bob = {"Authorization": f"Bearer {bob}"}
    r = await client.get(f"/api/v1/documents/{doc_id}", headers=h_bob)
    assert r.status_code == 404
