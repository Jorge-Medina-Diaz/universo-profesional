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
import urllib.parse

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
async def test_mcp_oauth_full_flow(client: AsyncClient) -> None:
    email = "jorge@webtools.es"
    password = "S3cur3-Passw0rd!"
    await _register_user(client, email, password)

    # Upgrade to Premium so MCP is allowed (the mock webhook works without auth)
    me = (await client.post("/api/v1/auth/login", json={"email": email, "password": password})).json()
    upgrade = await client.post(
        "/api/v1/billing/webhook/test",
        json={"event": "checkout.completed", "user_id": me["user_id"], "plan": "premium"},
    )
    assert upgrade.status_code == 200, upgrade.text

    # 1) DCR
    redirect_uri = "http://127.0.0.1:8765/callback"
    dcr = await client.post(
        "/auth/oauth/register",
        json={
            "client_name": "test-mcp-client",
            "redirect_uris": [redirect_uri],
            "scope": "universe:read universe:write documents:generate",
        },
    )
    assert dcr.status_code == 200, dcr.text
    client_id = dcr.json()["client_id"]

    # 2) Authorize (POST simulates consent)
    verifier, challenge = _pkce_pair()
    resource = client.base_url.scheme + "://" + (client.base_url.host or "test") + "/mcp"  # type: ignore[union-attr]
    # The app's `canonical_base_url` is `http://localhost:8000` by default in
    # config; we must use the same string the token validator checks against.
    from src.shared.config import get_settings

    resource = get_settings().mcp_canonical_uri

    auth_resp = await client.post(
        "/auth/oauth/authorize",
        data={
            "email": email,
            "password": password,
            "consent": "approve",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "universe:read universe:write documents:generate",
            "state": "xyz",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "resource": resource,
        },
        follow_redirects=False,
    )
    assert auth_resp.status_code == 302, auth_resp.text
    location = auth_resp.headers["location"]
    qs = urllib.parse.urlparse(location).query
    code = urllib.parse.parse_qs(qs)["code"][0]

    # 3) Token exchange
    tok_resp = await client.post(
        "/auth/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "code_verifier": verifier,
            "resource": resource,
        },
    )
    assert tok_resp.status_code == 200, tok_resp.text
    tokens = tok_resp.json()
    access = tokens["access_token"]
    assert tokens["token_type"] == "Bearer"
    assert tokens["refresh_token"]

    # 4) MCP initialize
    init = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert init.status_code == 200, init.text
    assert init.json()["result"]["protocolVersion"] == "2025-11-25"

    # 5) tools/list
    tl = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        headers={"Authorization": f"Bearer {access}"},
    )
    tools_names = {t["name"] for t in tl.json()["result"]["tools"]}
    assert {"get_universe_summary", "add_education", "match_job_to_profile", "generate_cv"} <= tools_names

    # 6) tools/call: add_education
    ce = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "add_education", "arguments": {"institution": "UCM", "degree": "Licenciado"}},
        },
        headers={"Authorization": f"Bearer {access}"},
    )
    assert ce.status_code == 200, ce.text

    # 7) tools/call: get_universe_summary
    summ = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "get_universe_summary", "arguments": {}},
        },
        headers={"Authorization": f"Bearer {access}"},
    )
    assert summ.status_code == 200, summ.text


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
