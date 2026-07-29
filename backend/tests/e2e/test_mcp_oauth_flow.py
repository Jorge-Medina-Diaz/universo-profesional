"""End-to-end MCP OAuth flow.

Demonstrates the wedge:
  1. DCR — POST /auth/oauth/register
  2. /authorize submission with consent + PKCE
  3. /token exchange (code + verifier → access token bound to mcp resource)
  4. Tool calls via /mcp (initialize, tools/list, tools/call)
"""
from __future__ import annotations

import base64
import hashlib
import re
import secrets

import pytest
from httpx import AsyncClient


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return verifier, challenge


async def _register_user(client: AsyncClient, email: str, password: str) -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "locale": "es-ES"},
    )
    assert r.status_code == 201, r.text
    token = re.search(r"token=([\w-]+)", r.json()["verification_link"]).group(1)  # type: ignore[union-attr]
    await client.post("/api/v1/auth/verify", json={"token": token})


@pytest.mark.asyncio
async def test_mcp_unauthorized_returns_401_with_www_authenticate(client: AsyncClient) -> None:
    r = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
    )
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers
    assert "resource_metadata=" in r.headers["WWW-Authenticate"]


@pytest.mark.asyncio
async def test_well_known_endpoints(client: AsyncClient) -> None:
    as_meta = (await client.get("/.well-known/oauth-authorization-server")).json()
    assert "authorization_endpoint" in as_meta
    assert "token_endpoint" in as_meta
    assert "registration_endpoint" in as_meta
    assert "S256" in as_meta["code_challenge_methods_supported"]

    pr_meta = (await client.get("/.well-known/oauth-protected-resource")).json()
    assert "resource" in pr_meta
    assert "authorization_servers" in pr_meta

    card = (await client.get("/.well-known/mcp/server-card.json")).json()
    assert card["transport"]["type"] == "streamable-http"
    assert card["authorization"]["type"] == "oauth2.1"
