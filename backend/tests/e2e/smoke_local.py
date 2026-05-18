"""Smoke script run *against the live docker-compose stack*.

Verifies the golden path end-to-end:
  1. Health + well-known endpoints
  2. Register → verify → login → fetch /me
  3. Add education + experience + skill
  4. Generate CV (mock LLM + WeasyPrint PDF)
  5. Download PDF
  6. MCP OAuth flow (DCR → authorize → token → tools/list → tools/call)

Run inside the backend container after `alembic upgrade head`:
    docker compose exec backend python -m tests.e2e.smoke_local
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import re
import secrets
import sys
import urllib.parse
from typing import Any

import httpx

BASE = "http://localhost:8000"  # When run from host
# When run *inside* the backend container, swap to the in-container URL:
if "--in-container" in sys.argv:
    BASE = "http://localhost:8000"


def _pkce() -> tuple[str, str]:
    v = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    c = base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode()
    return v, c


async def main() -> int:
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        # 0) Health + metadata
        r = await c.get("/health")
        assert r.status_code == 200, r.text
        for path in (
            "/.well-known/oauth-authorization-server",
            "/.well-known/oauth-protected-resource",
            "/.well-known/mcp/server-card.json",
            "/.well-known/jwks.json",
        ):
            assert (await c.get(path)).status_code == 200, path
        print("✓ Health + well-known endpoints")

        # 1) Register
        import time
        email = f"smoke-{int(time.time())}@webtools.es"
        password = "S3cur3-Passw0rd!"
        r = await c.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "locale": "es-ES"},
        )
        assert r.status_code == 201, r.text
        token = re.search(r"token=([\w-]+)", r.json()["verification_link"]).group(1)

        # 2) Verify + login
        assert (await c.post("/api/v1/auth/verify", json={"token": token})).status_code == 200
        r = await c.post("/api/v1/auth/login", json={"email": email, "password": password})
        tokens = r.json()
        H = {"Authorization": f"Bearer {tokens['access_token']}"}
        print(f"✓ Registered + logged in as {email}")

        # 3) Add universe entries
        await c.post(
            "/api/v1/universe/education",
            headers=H,
            json={"institution": "UCM", "degree": "Ingeniería Informática"},
        )
        await c.post(
            "/api/v1/universe/experience",
            headers=H,
            json={
                "organization": "Acme",
                "role": "Senior Python Engineer",
                "description": "FastAPI backend, PostgreSQL",
                "highlights": ["3x throughput improvement"],
                "competences": ["Python", "FastAPI"],
            },
        )
        await c.post(
            "/api/v1/universe/skill",
            headers=H,
            json={"name": "Python", "category": "hard", "level": "expert"},
        )
        summary = (await c.get("/api/v1/universe/summary", headers=H)).json()
        assert summary["counts"]["experiences"] >= 1
        print(f"✓ Universe entries created (counts: {summary['counts']})")

        # 4) Generate CV
        r = await c.post(
            "/api/v1/documents/generate-cv",
            headers=H,
            json={"job_description": "Senior Python Backend, FastAPI, PostgreSQL", "language": "es"},
        )
        assert r.status_code == 201, r.text
        doc = r.json()
        print(f"✓ CV generated id={doc['document_id']}")

        # 5) Download PDF
        if doc["pdf_url"]:
            url = doc["pdf_url"].replace(BASE, "")
            r = await c.get(url, headers=H)
            assert r.status_code == 200, r.text
            print(f"✓ PDF downloaded ({len(r.content)} bytes)")

        # 6) MCP OAuth flow
        # Upgrade to premium so MCP is allowed
        await c.post(
            "/api/v1/billing/webhook/test",
            json={"event": "checkout.completed", "user_id": tokens["user_id"], "plan": "premium"},
        )

        redirect = "http://127.0.0.1:8765/callback"
        dcr = (
            await c.post(
                "/auth/oauth/register",
                json={
                    "client_name": "smoke-mcp",
                    "redirect_uris": [redirect],
                    "scope": "universe:read universe:write documents:generate",
                },
            )
        ).json()
        client_id = dcr["client_id"]
        verifier, challenge = _pkce()
        from src.shared.config import get_settings

        resource = get_settings().mcp_canonical_uri
        auth_resp = await c.post(
            "/auth/oauth/authorize",
            data={
                "email": email,
                "password": password,
                "consent": "approve",
                "client_id": client_id,
                "redirect_uri": redirect,
                "scope": "universe:read universe:write documents:generate",
                "state": "x",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": resource,
            },
            follow_redirects=False,
        )
        location = auth_resp.headers["location"]
        code = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)["code"][0]
        tok = (
            await c.post(
                "/auth/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect,
                    "client_id": client_id,
                    "code_verifier": verifier,
                    "resource": resource,
                },
            )
        ).json()
        access = tok["access_token"]
        print(f"✓ MCP OAuth: DCR + authorize + token grant ok")

        # tools/list
        r = await c.post(
            "/mcp",
            headers={"Authorization": f"Bearer {access}"},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )
        names = {t["name"] for t in r.json()["result"]["tools"]}
        assert "generate_cv" in names and "match_job_to_profile" in names
        print(f"✓ MCP tools/list returned {len(names)} tools")

        # tools/call match_job_to_profile
        r = await c.post(
            "/mcp",
            headers={"Authorization": f"Bearer {access}"},
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "match_job_to_profile",
                    "arguments": {"job_description": "Senior Python developer with FastAPI"},
                },
            },
        )
        assert r.status_code == 200, r.text
        print("✓ MCP tools/call match_job_to_profile ok")

    print("\n✅ Smoke verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
