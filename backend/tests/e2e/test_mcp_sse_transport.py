"""E2E tests for the MCP SSE transport using the official SDK.

``httpx.ASGITransport`` buffers the entire response body before returning it
to the caller, which makes it incompatible with long-lived SSE streams.
These tests therefore use ``asgiref.testing.ApplicationCommunicator`` to drive
the ASGI app directly and receive each SSE chunk incrementally.
"""
from __future__ import annotations

import json
import urllib.parse

import pytest
from asgiref.testing import ApplicationCommunicator
from httpx import AsyncClient

from tests.e2e.test_mcp_oauth_flow import _pkce_pair, _register_user


class _McpSseClient:
    """Test helper that speaks MCP over SSE using ApplicationCommunicator."""

    def __init__(self, app, token: str) -> None:
        self.app = app
        self.token = token
        self._msg_id = 0
        self._sse_comm: ApplicationCommunicator | None = None
        self._endpoint: str | None = None

    async def connect(self) -> str:
        self._sse_comm = ApplicationCommunicator(
            self.app,
            {
                "type": "http",
                "http_version": "1.1",
                "method": "GET",
                "path": "/mcp/sse",
                "query_string": b"",
                "headers": [
                    [b"host", b"test"],
                    [b"authorization", f"Bearer {self.token}".encode()],
                ],
            },
        )
        start = await self._sse_comm.receive_output(timeout=5)
        assert start["type"] == "http.response.start"
        assert start["status"] == 200

        body = await self._sse_comm.receive_output(timeout=5)
        assert body["type"] == "http.response.body"
        self._endpoint = self._parse_endpoint(body["body"])
        return self._endpoint

    @staticmethod
    def _parse_endpoint(body: bytes) -> str:
        for line in body.decode().strip().split("\n"):
            if line.startswith("data:"):
                return line[5:].strip()
        raise ValueError("No endpoint event in SSE body")

    async def send(self, method: str, params: dict | None = None) -> int:
        self._msg_id += 1
        msg = {
            "jsonrpc": "2.0",
            "id": self._msg_id,
            "method": method,
            "params": params or {},
        }
        # POST messages have a short "Accepted" response, so we can use
        # ApplicationCommunicator for them as well.
        assert self._endpoint is not None
        path, _, qs = self._endpoint.partition("?")
        comm = ApplicationCommunicator(
            self.app,
            {
                "type": "http",
                "http_version": "1.1",
                "method": "POST",
                "path": path,
                "query_string": qs.encode(),
                "headers": [
                    [b"host", b"test"],
                    [b"content-type", b"application/json"],
                    [b"authorization", f"Bearer {self.token}".encode()],
                ],
            },
        )
        await comm.send_input(
            {"type": "http.request", "body": json.dumps(msg).encode(), "more_body": False}
        )
        start = await comm.receive_output(timeout=5)
        assert start["type"] == "http.response.start"
        assert start["status"] == 202
        body = await comm.receive_output(timeout=5)
        assert body["type"] == "http.response.body"
        return self._msg_id

    async def receive(self) -> dict:
        assert self._sse_comm is not None
        body = await self._sse_comm.receive_output(timeout=5)
        assert body["type"] == "http.response.body"
        return self._parse_sse_message(body["body"])

    @staticmethod
    def _parse_sse_message(body: bytes) -> dict:
        for line in body.decode().strip().split("\n"):
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        raise ValueError("No data event in SSE body")

    async def close(self) -> None:
        if self._sse_comm:
            self._sse_comm.stop()
            await self._sse_comm.wait(timeout=2)


@pytest.mark.asyncio
async def test_mcp_sse_initialize_list_tools_and_call(client: AsyncClient, _app) -> None:
    """Full SSE E2E: connect, initialize, list tools, call a tool."""
    # 1. Register user and upgrade to premium
    email = "sse_e2e@example.com"
    password = "S3cur3-Passw0rd!"
    await _register_user(client, email, password)

    me = (await client.post("/api/v1/auth/login", json={"email": email, "password": password})).json()
    upgrade = await client.post(
        "/api/v1/billing/webhook/test",
        json={"event": "checkout.completed", "user_id": me["user_id"], "plan": "premium"},
    )
    assert upgrade.status_code == 200

    # 2. DCR + PKCE to obtain MCP-scoped token
    redirect_uri = "http://127.0.0.1:8765/callback"
    dcr = await client.post(
        "/auth/oauth/register",
        json={
            "client_name": "test-mcp-sse-client",
            "redirect_uris": [redirect_uri],
            "scope": "universe:read universe:write documents:generate",
        },
    )
    assert dcr.status_code == 200
    client_id = dcr.json()["client_id"]

    verifier, challenge = _pkce_pair()
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
    assert auth_resp.status_code == 302
    location = auth_resp.headers["location"]
    qs = urllib.parse.urlparse(location).query
    code = urllib.parse.parse_qs(qs)["code"][0]

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
    assert tok_resp.status_code == 200
    access = tok_resp.json()["access_token"]

    # 3. Connect SSE
    mcp = _McpSseClient(_app, access)
    endpoint = await mcp.connect()
    assert "/messages/?session_id=" in endpoint

    # 4. Initialize
    await mcp.send(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"},
        },
    )
    result = await mcp.receive()
    assert result["id"] == 1
    assert result["result"]["protocolVersion"] in {"2024-11-05", "2025-11-25"}
    assert result["result"]["serverInfo"]["name"] == "cvs-saas-mcp"

    # 5. List tools
    await mcp.send("tools/list")
    result = await mcp.receive()
    assert result["id"] == 2
    tools = {t["name"] for t in result["result"]["tools"]}
    assert "read_universe_summary" in tools
    assert "create_entity" in tools
    assert "generate_cv" in tools

    # 6. Call a read tool
    await mcp.send(
        "tools/call",
        {"name": "read_universe_summary", "arguments": {}},
    )
    result = await mcp.receive()
    assert result["id"] == 3
    content = json.loads(result["result"]["content"][0]["text"])
    assert "counts" in content

    await mcp.close()
