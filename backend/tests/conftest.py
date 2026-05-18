"""Pytest fixtures: app, async client, DB session per test (cleaned via TRUNCATE)."""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://cvs:cvs_dev_password@postgres:5432/cvs")
os.environ.setdefault("REDIS_URL", "redis://redis:6379/1")
os.environ.setdefault("ENV", "test")

# Defer imports until env is set
from src.main import app  # noqa: E402
from src.shared.db import dispose_engine, get_session_factory  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def _app():  # noqa: PT005
    async with app.router.lifespan_context(app):
        yield app
        await dispose_engine()


@pytest_asyncio.fixture
async def client(_app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def _clean_db() -> AsyncIterator[None]:
    """TRUNCATE every table between tests to keep them isolated."""
    factory = get_session_factory()
    async with factory() as session:
        # The order doesn't matter with CASCADE.
        tables = (
            "domain_events quota_usage subscriptions mcp_invocations oauth_tokens "
            "oauth_authorization_codes oauth_clients applications documents jobs "
            "goals career_preferences interests achievements languages courses "
            "certifications skills projects experiences educations universes "
            "refresh_tokens email_tokens users"
        ).split()
        await session.execute(text(f"TRUNCATE {', '.join(tables)} CASCADE"))
        await session.commit()
    yield
