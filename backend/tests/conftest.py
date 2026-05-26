"""Pytest fixtures: app, async client, DB session per test (cleaned via TRUNCATE)."""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

# Default to a DEDICATED test database. The autouse fixture below TRUNCATEs
# every table between tests — pointing this at the shared dev DB (`cvs`) would
# wipe real data, which has bitten us before. Create it once with:
#   docker exec cvs-postgres createdb -U cvs cvs_test
#   DATABASE_URL=...cvs_test alembic upgrade head
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://cvs:cvs_dev_password@localhost:5432/cvs_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

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


def _assert_test_database() -> None:
    """Hard guard: never TRUNCATE a database that isn't clearly a test DB.

    A misconfigured DATABASE_URL pointing at dev/prod would otherwise be
    silently wiped by the autouse fixture. We refuse loudly instead.
    """
    from src.shared.config import get_settings

    db_name = get_settings().database_url.rsplit("/", 1)[-1].split("?")[0]
    if "test" not in db_name.lower():
        msg = (
            f"Refusing to TRUNCATE database {db_name!r}: it does not look like a "
            "test database. Point DATABASE_URL at a dedicated DB whose name "
            "contains 'test' (e.g. cvs_test) before running the suite."
        )
        raise RuntimeError(msg)


@pytest_asyncio.fixture(autouse=True)
async def _clean_db() -> AsyncIterator[None]:
    """TRUNCATE every table between tests to keep them isolated."""
    _assert_test_database()
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
