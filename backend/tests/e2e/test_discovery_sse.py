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
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from src.agents.interfaces.api.router import discovery_progress_stream
from src.shared.db import get_session_factory, with_user_session
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
async def test_discovery_stream_returns_sse_headers() -> None:
    """With a valid token the endpoint negotiates an SSE stream.

    Deliberately NOT driven through the `client` fixture. The body of this
    endpoint never ends, and `httpx.ASGITransport` is not a streaming
    transport — it runs the ASGI app until the final body chunk before
    returning, so *any* request to an infinite stream (including
    `client.stream()`) blocks forever. This test used to do exactly that and
    hung the whole suite. Calling the route directly asserts the same
    contract — auth accepted, SSE negotiated — and terminates.
    """
    access_token = encode_jwt(
        {"sub": "00000000-0000-0000-0000-000000000002", "aud": "cvs-saas-api", "type": "access"}
    )
    request = AsyncMock()
    request.headers = {"authorization": f"Bearer {access_token}"}
    request.is_disconnected = AsyncMock(return_value=True)

    response = await discovery_progress_stream(request)

    assert response.status_code == 200
    assert response.media_type == "text/event-stream"


@pytest.mark.asyncio
async def test_discovery_stream_heartbeat_and_event() -> None:
    """The generator yields heartbeats and emits DB rows as SSE events."""
    # 1. Create a real user and JWT
    from datetime import datetime as _dt

    from src.identity.domain.user import User
    from src.identity.infrastructure.repositories import SqlAlchemyUserRepository
    from src.shared.security import hash_password
    from src.shared.value_objects import Email

    factory = get_session_factory()
    async with factory() as session:
        # The repository persists an aggregate; it has no `create()` factory.
        user = User.register(
            email=Email("sse_gen@example.com"),
            password_hash=hash_password("S3cur3-Passw0rd!"),
            display_name=None,
            locale="es-ES",
            now=_dt.now(UTC),
        )
        user.mark_verified(now=_dt.now(UTC))
        await SqlAlchemyUserRepository(session).save(user)
        await session.commit()
        user_id = user.id

    access_token = encode_jwt({"sub": str(user_id), "aud": "cvs-saas-api", "type": "access"})

    # 2. Build a mock request that carries the Bearer token and is never
    #    considered disconnected.
    request = AsyncMock()
    request.headers = {"authorization": f"Bearer {access_token}"}
    request.is_disconnected = AsyncMock(return_value=False)

    response = await discovery_progress_stream(request)
    assert response.media_type == "text/event-stream"

    body = response.body_iterator
    assert hasattr(body, "__aiter__")
    chunks: list[str] = []

    async def _collect() -> None:
        async for chunk in body:
            chunks.append(chunk)
            if "entity_discovered" in chunk:
                break

    async def _seed() -> None:
        # The generator anchors `last_seen_at` to "now" on its first iteration,
        # so a row written BEFORE it starts is invisible by design. Write after
        # it is running — which is also the behaviour that actually matters:
        # a live change reaching a connected client.
        await asyncio.sleep(0.5)
        # `universe_change_log` is RLS-protected; a bare factory() session is
        # rejected with "new row violates row-level security policy".
        async with with_user_session(user_id) as session:
            await session.execute(
                text(
                    """
                    INSERT INTO universe_change_log (
                        user_id, entity_id, entity_type, change_type, source,
                        new_value, changed_at
                    ) VALUES (
                        :uid, :eid, 'skill', 'create', 'test',
                        '{"name": "Python"}'::jsonb, :ts
                    )
                    """
                ),
                {"uid": str(user_id), "eid": str(uuid4()), "ts": datetime.now(UTC)},
            )
            await session.commit()

    try:
        await asyncio.wait_for(asyncio.gather(_collect(), _seed()), timeout=20.0)
    except TimeoutError:
        pytest.fail(f"SSE generator did not yield the expected event. Got: {chunks}")

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
    body = response.body_iterator
    chunks: list[str] = []
    async for chunk in body:  # type: ignore[attr-defined]
        chunks.append(chunk)

    # Should yield nothing because we disconnect before the first iteration.
    assert chunks == []
