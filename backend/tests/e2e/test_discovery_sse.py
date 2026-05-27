"""E2E tests for the discovery SSE stream endpoint.

Because ``httpx.ASGITransport`` buffers the full response body, we cannot
reliably consume the SSE stream through the HTTP client.  Instead we:

  1. Test auth / HTTP contract via the normal client fixture.
  2. Test event generation by calling ``discovery_progress_stream`` directly
     with a mocked request that carries a valid JWT.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from src.agents.interfaces.api.router import discovery_progress_stream
from src.shared.db import get_session_factory
from src.shared.security import encode_jwt


async def _register_and_login(client: AsyncClient) -> str:
    """Register, verify and return an access token."""
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "discovery@example.com", "password": "S3cur3-Passw0rd!", "locale": "es-ES"},
    )
    assert r.status_code == 201, r.text
    token = re.search(r"token=([\w-]+)", r.json()["verification_link"]).group(1)  # type: ignore[union-attr]
    v = await client.post("/api/v1/auth/verify", json={"token": token})
    assert v.status_code == 200, v.text
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "discovery@example.com", "password": "S3cur3-Passw0rd!"},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_discovery_stream_requires_auth(client: AsyncClient) -> None:
    """Anonymous requests must 401."""
    r = await client.get("/api/v1/agents/discovery/stream")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_discovery_stream_returns_sse_headers(client: AsyncClient) -> None:
    """With a valid token the endpoint negotiates an SSE stream."""
    access = await _register_and_login(client)
    # We cannot read the infinite body through ASGITransport, but we can
    # verify the response was initiated with the right headers.
    response = await client.get(
        "/api/v1/agents/discovery/stream",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_discovery_stream_heartbeat_and_event() -> None:
    """The generator yields heartbeats and emits DB rows as SSE events."""
    # 1. Create a real user and JWT
    from src.identity.infrastructure.repositories import SqlAlchemyUserRepository
    from src.shared.security import hash_password

    factory = get_session_factory()
    async with factory() as session:
        repo = SqlAlchemyUserRepository(session)
        user = await repo.create(
            email="sse_gen@example.com",
            password_hash=hash_password("S3cur3-Passw0rd!"),
            locale="es-ES",
            is_verified=True,
        )
        await session.commit()
        user_id = user.id

    access_token = encode_jwt({"sub": str(user_id), "aud": "cvs-saas-api", "type": "access"})

    # 2. Seed a change-log row with a timestamp slightly in the past so the
    #    generator's first poll picks it up.
    past = datetime.now(UTC) - timedelta(seconds=1)
    async with factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO universe_change_log (
                    user_id, entity_type, change_type, source, new_value, changed_at
                ) VALUES (
                    :uid, 'skill', 'create', 'test',
                    '{"name": "Python"}'::jsonb, :ts
                )
                """
            ),
            {"uid": str(user_id), "ts": past},
        )
        await session.commit()

    # 3. Build a mock request that carries the Bearer token and is never
    #    considered disconnected.
    request = AsyncMock()
    request.headers = {"authorization": f"Bearer {access_token}"}
    request.is_disconnected = AsyncMock(return_value=False)

    response = await discovery_progress_stream(request)
    assert response.media_type == "text/event-stream"

    # 4. Consume the generator with a wall-clock timeout so the infinite
    #    loop doesn't hang the test.
    body = response.body
    assert hasattr(body, "__aiter__")
    chunks: list[str] = []

    async def _collect() -> None:
        async for chunk in body:  # type: ignore[attr-defined]
            chunks.append(chunk)
            if "entity_discovered" in chunk:
                break

    try:
        await asyncio.wait_for(_collect(), timeout=8.0)
    except TimeoutError:
        pytest.fail("SSE generator did not yield the expected event within 8s")

    # 5. Assertions
    assert any(":heartbeat" in c for c in chunks), f"No heartbeat in chunks: {chunks}"
    event_chunks = [c for c in chunks if c.startswith("data:")]
    assert event_chunks, f"No data event in chunks: {chunks}"
    payload = json.loads(event_chunks[0].replace("data: ", ""))
    assert payload["type"] == "entity_discovered"
    assert payload["entity_type"] == "skill"
    assert payload["name"] == "Python"


@pytest.mark.asyncio
async def test_discovery_stream_respects_disconnect() -> None:
    """When the client disconnects the generator stops polling."""
    access_token = encode_jwt({"sub": "00000000-0000-0000-0000-000000000001", "aud": "cvs-saas-api", "type": "access"})

    request = AsyncMock()
    request.headers = {"authorization": f"Bearer {access_token}"}
    # Simulate immediate disconnect
    request.is_disconnected = AsyncMock(return_value=True)

    response = await discovery_progress_stream(request)
    body = response.body
    chunks: list[str] = []
    async for chunk in body:  # type: ignore[attr-defined]
        chunks.append(chunk)

    # Should yield nothing because we disconnect before the first iteration.
    assert chunks == []
