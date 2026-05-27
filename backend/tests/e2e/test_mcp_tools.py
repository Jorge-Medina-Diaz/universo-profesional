"""E2E-style tests for MCP SDK tools.

These tests exercise the tool handlers registered in ``src.mcp_server.tools``
directly (same code-path as the SSE transport) because ``httpx.ASGITransport``
buffers the entire response body and therefore cannot stream SSE.  Auth and
OAuth flow are covered by ``test_mcp_oauth_flow.py``.
"""
from __future__ import annotations

import re
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from src.mcp_server.tools import _TOOL_SCOPES, TOOL_HANDLERS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _call_tool(name: str, user_id: UUID, args: dict[str, Any] | None = None) -> Any:
    """Invoke an SDK tool handler directly."""
    handler = TOOL_HANDLERS[name]
    return await handler(user_id=user_id, args=args or {})


async def _create_user(client: AsyncClient, email: str, password: str) -> UUID:
    """Register, verify and return a user id."""
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "locale": "es-ES"},
    )
    assert r.status_code == 201, r.text
    token = re.search(r"token=([\w-]+)", r.json()["verification_link"]).group(1)
    v = await client.post("/api/v1/auth/verify", json={"token": token})
    assert v.status_code == 200, v.text
    me = (await client.post("/api/v1/auth/login", json={"email": email, "password": password})).json()
    return UUID(me["user_id"])


async def _seed_education(client: AsyncClient, token: str, institution: str, degree: str) -> UUID:
    r = await client.post(
        "/api/v1/universe/education",
        json={"institution": institution, "degree": degree},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return UUID(r.json()["id"])


async def _seed_skill(client: AsyncClient, token: str, name: str, level: str = "intermediate") -> UUID:
    r = await client.post(
        "/api/v1/universe/skill",
        json={"name": name, "category": "hard", "level": level},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return UUID(r.json()["id"])


async def _get_token(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ---------------------------------------------------------------------------
# Tool definitions & scopes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tools_list_contains_expected_names(client: AsyncClient) -> None:
    """Sanity: the in-memory tool registry has the tools we document."""
    names = set(TOOL_HANDLERS)
    expected = {
        "read_universe_summary",
        "read_entity",
        "search_entities",
        "list_entities",
        "create_entity",
        "update_entity",
        "delete_entity",
        "link_esco",
        "get_discovery_progress",
        "generate_cv",
    }
    assert expected <= names


@pytest.mark.asyncio
async def test_tool_scopes_are_defined(client: AsyncClient) -> None:
    for name in TOOL_HANDLERS:
        assert name in _TOOL_SCOPES, f"Missing scope mapping for {name}"


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_universe_summary_empty(client: AsyncClient) -> None:
    user_id = await _create_user(client, "empty2@example.com", "S3cur3-Passw0rd!")
    result = await _call_tool("read_universe_summary", user_id, {})
    assert isinstance(result, dict)
    assert "counts" in result


@pytest.mark.asyncio
async def test_list_and_read_entity(client: AsyncClient) -> None:
    user_id = await _create_user(client, "entity2@example.com", "S3cur3-Passw0rd!")
    token = await _get_token(client, "entity2@example.com", "S3cur3-Passw0rd!")
    eid = await _seed_education(client, token, "MIT", "BS Computer Science")

    # list_entities
    result = await _call_tool("list_entities", user_id, {"entity_type": "education"})
    assert isinstance(result, list)
    assert any(r["institution"] == "MIT" for r in result)

    # read_entity by id
    result = await _call_tool("read_entity", user_id, {"entity_type": "education", "id": str(eid)})
    assert result["entity"]["institution"] == "MIT"


@pytest.mark.asyncio
async def test_search_entities(client: AsyncClient) -> None:
    user_id = await _create_user(client, "search2@example.com", "S3cur3-Passw0rd!")
    token = await _get_token(client, "search2@example.com", "S3cur3-Passw0rd!")
    await _seed_skill(client, token, "Rust", "expert")

    result = await _call_tool("search_entities", user_id, {"query": "Rust"})
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# HITL write tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_entity_returns_proposal(client: AsyncClient) -> None:
    user_id = await _create_user(client, "proposal2@example.com", "S3cur3-Passw0rd!")
    result = await _call_tool(
        "create_entity",
        user_id,
        {"entity_type": "skill", "data": {"name": "Rust", "category": "hard", "level": "intermediate"}},
    )
    assert "proposal_id" in result
    assert result["action"] == "create"
    assert result["entity_type"] == "skill"

    # Confirm via proposal store so the DB stays clean for other tests
    from src.agents.infrastructure.proposal_store import delete_proposal, get_proposal

    proposal = get_proposal(str(user_id), result["proposal_id"])
    assert proposal is not None
    delete_proposal(str(user_id), result["proposal_id"])


@pytest.mark.asyncio
async def test_update_entity_returns_proposal(client: AsyncClient) -> None:
    user_id = await _create_user(client, "update2@example.com", "S3cur3-Passw0rd!")
    token = await _get_token(client, "update2@example.com", "S3cur3-Passw0rd!")
    sid = await _seed_skill(client, token, "Go", "basic")

    result = await _call_tool(
        "update_entity",
        user_id,
        {"entity_type": "skill", "entity_id": str(sid), "data": {"level": "expert"}},
    )
    assert "proposal_id" in result
    assert result["action"] == "update"

    # Confirm
    from src.agents.infrastructure.proposal_store import delete_proposal

    delete_proposal(str(user_id), result["proposal_id"])


@pytest.mark.asyncio
async def test_delete_entity_returns_proposal(client: AsyncClient) -> None:
    user_id = await _create_user(client, "delete2@example.com", "S3cur3-Passw0rd!")
    token = await _get_token(client, "delete2@example.com", "S3cur3-Passw0rd!")
    iid = await _seed_education(client, token, "Temp", "ToDelete")

    result = await _call_tool(
        "delete_entity",
        user_id,
        {"entity_type": "education", "entity_id": str(iid)},
    )
    assert "proposal_id" in result
    assert result["action"] == "delete"

    # Confirm
    from src.agents.infrastructure.proposal_store import delete_proposal

    delete_proposal(str(user_id), result["proposal_id"])


# ---------------------------------------------------------------------------
# ESCO, discovery, CV
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_link_esco(client: AsyncClient) -> None:
    user_id = await _create_user(client, "esco2@example.com", "S3cur3-Passw0rd!")
    result = await _call_tool("link_esco", user_id, {"text": "Python programming", "kind": "skill"})
    assert "state" in result
    assert result["state"] in {"linked", "suggested", "orphan"}


@pytest.mark.asyncio
async def test_get_discovery_progress(client: AsyncClient) -> None:
    # Skip if AGE graph tables are not present in the test database
    from sqlalchemy import text
    from src.shared.db import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        try:
            await session.execute(text("SELECT count(*) FROM universe_personal.Experience"))
        except Exception as exc:
            pytest.skip(f"AGE graph not available in test DB: {exc}")

    user_id = await _create_user(client, "discover2@example.com", "S3cur3-Passw0rd!")
    result = await _call_tool("get_discovery_progress", user_id, {})
    assert "discovery_score" in result
    assert 0 <= result["discovery_score"] <= 100
    assert "counts" in result


@pytest.mark.asyncio
async def test_generate_cv(client: AsyncClient) -> None:
    user_id = await _create_user(client, "cv2@example.com", "S3cur3-Passw0rd!")
    token = await _get_token(client, "cv2@example.com", "S3cur3-Passw0rd!")
    await _seed_education(client, token, "Stanford", "MS")
    await client.post(
        "/api/v1/universe/experience",
        json={"organization": "Acme", "role": "Engineer"},
        headers={"Authorization": f"Bearer {token}"},
    )

    result = await _call_tool(
        "generate_cv",
        user_id,
        {"language": "es", "tone": "professional", "job_description": "Software engineer with Python experience"},
    )
    assert "document_id" in result
    assert "pdf_url" in result


# ---------------------------------------------------------------------------
# Permission boundaries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cannot_read_another_users_data(client: AsyncClient) -> None:
    await _create_user(client, "alice2@example.com", "S3cur3-Passw0rd!")
    bob = await _create_user(client, "bob2@example.com", "S3cur3-Passw0rd!")
    alice_token = await _get_token(client, "alice2@example.com", "S3cur3-Passw0rd!")

    eid = await _seed_education(client, alice_token, "Alice-U", "Degree")

    with pytest.raises(ValueError, match="not found"):
        await _call_tool("read_entity", bob, {"entity_type": "education", "id": str(eid)})
