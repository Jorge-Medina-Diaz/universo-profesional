"""Pytest fixtures: app, async client, DB session per test (cleaned via DELETE)."""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

# Default to a DEDICATED test database. The autouse fixture below DELETEs
# every table between tests — pointing this at the shared dev DB (`cvs`) would
# wipe real data, which has bitten us before. Create it once with:
#   docker exec cvs-postgres createdb -U cvs cvs_test
#   DATABASE_URL=...cvs_test alembic upgrade head
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://cvs:cvs_dev_password@localhost:5432/cvs_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

# Defer imports until env is set
from src.main import app
from src.shared.db import dispose_engine, get_session_factory


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def _app():
    # Force embedding scheduler to use in-process fallback (no arq pool)
    # so tests don't depend on Redis background workers.
    from src.universe.infrastructure.scheduler import ArqEmbeddingScheduler

    async def _noop_pool(self):  # type: ignore[no-untyped-def]
        return None

    ArqEmbeddingScheduler._get_pool = _noop_pool  # type: ignore[method-assign]

    async with app.router.lifespan_context(app):
        yield app
        await dispose_engine()


@pytest_asyncio.fixture
async def client(_app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac


def _assert_test_database() -> None:
    """Hard guard: never clean a database that isn't clearly a test DB.

    A misconfigured DATABASE_URL pointing at dev/prod would otherwise be
    silently wiped by the autouse fixture. We refuse loudly instead.
    """
    from src.shared.config import get_settings

    db_name = get_settings().database_url.rsplit("/", 1)[-1].split("?")[0]
    if "test" not in db_name.lower():
        msg = (
            f"Refusing to clean database {db_name!r}: it does not look like a "
            "test database. Point DATABASE_URL at a dedicated DB whose name "
            "contains 'test' (e.g. cvs_test) before running the suite."
        )
        raise RuntimeError(msg)


@pytest_asyncio.fixture(autouse=True)
async def _clean_db() -> AsyncIterator[None]:
    """Wipe all user data between tests using DELETE instead of TRUNCATE.

    TRUNCATE ... CASCADE takes AccessExclusiveLock on every target table.
    When multiple pytest-xdist workers hit the same DB they deadlock on
    these locks.  DELETE only needs RowExclusiveLock and, because every
    FK to ``users.id`` has ``ON DELETE CASCADE``, ``DELETE FROM users``
    cascades to virtually every other table automatically.

    We also flush the Redis test DB so cached summaries / tokens don't
    leak across tests.
    """
    _assert_test_database()
    factory = get_session_factory()
    async with factory() as session:
        # Cascade delete from the root user table.
        await session.execute(text("DELETE FROM users"))
        # Belt-and-suspenders: explicitly delete tables that might not
        # cascade from users (defensive for future migrations).
        tables = ["domain_events", "quota_usage", "subscriptions", "mcp_invocations", "oauth_tokens", "oauth_authorization_codes", "oauth_clients", "applications", "documents", "jobs", "goals", "career_preferences", "interests", "achievements", "languages", "courses", "certifications", "skills", "projects", "experiences", "educations", "universes", "refresh_tokens", "email_tokens"]
        for table in tables:
            await session.execute(text(f"DELETE FROM {table}"))
        await session.commit()

    # Flush Redis test DB so cached universe summaries, rate-limit counters,
    # etc. don't leak between tests.
    try:
        from src.shared.redis import get_redis

        redis = get_redis()
        await redis.flushdb()
    except Exception:
        # Redis may not be running in some local setups; don't fail the suite.
        pass
    yield
