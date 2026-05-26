"""Database engine, session factory, declarative Base, and RLS helpers.

Every request acquires a session via `get_session()`. Sessions set
`app.current_user_id` (used by RLS policies) when the request is authenticated.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings


class Base(DeclarativeBase):
    """Declarative Base used by every ORM model.

    All ORM models live under their respective `infrastructure/orm.py`.
    The `import_all_models()` helper below ensures Alembic sees every model.
    """


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is not None:
        return _engine
    settings = get_settings()
    if settings.is_test:
        # Tests run each async test in its own event loop; a pooled connection
        # created in one loop and closed at session teardown in another raises
        # "Task got Future attached to a different loop". NullPool opens/closes
        # a fresh connection per checkout within the same loop, eliminating the
        # cross-loop teardown crash. (Pooling matters for prod, not tests.)
        from sqlalchemy.pool import NullPool

        _engine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            poolclass=NullPool,
            pool_pre_ping=True,
        )
        return _engine
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
    )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is not None:
        return _session_factory
    _session_factory = async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        autoflush=False,
    )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — yields an AsyncSession scoped to the request."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def set_rls_user(session: AsyncSession, user_id: UUID | None) -> None:
    """Set Postgres session variable consumed by RLS policies.

    Note: `SET LOCAL` does not accept bind parameters in PostgreSQL, so we
    must inline the value. `user_id` is a UUID (already validated), so it is
    safe to interpolate as a literal.
    """
    if user_id is None:
        await session.execute(text("RESET app.current_user_id"))
        return
    # UUID() ensures the value is a well-formed UUID before interpolation.
    safe_uuid = str(UUID(str(user_id)))
    await session.execute(text(f"SET LOCAL app.current_user_id = '{safe_uuid}'"))


from contextlib import asynccontextmanager


@asynccontextmanager
async def with_user_session(user_id: UUID | None):
    """Yield an AsyncSession with RLS already set for the given user.

    Guarantees commit on success and rollback on exception.
    """
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, user_id)
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()


def import_all_models() -> None:
    """Import every ORM module so SQLAlchemy registers tables on `Base.metadata`.

    Called by Alembic env and by the FastAPI lifespan.
    """
    # noqa: F401 — imports for side effects (table registration)
    from src.billing.infrastructure import orm as _billing  # noqa: F401
    from src.coherence.infrastructure import orm as _coherence  # noqa: F401
    from src.documents.infrastructure import orm as _documents  # noqa: F401
    from src.identity.infrastructure import orm as _identity  # noqa: F401
    from src.integrations.infrastructure import orm as _integrations  # noqa: F401
    from src.mcp_server.infrastructure import orm as _mcp  # noqa: F401
    from src.notes.infrastructure import orm as _notes  # noqa: F401
    from src.universe.infrastructure import orm as _universe  # noqa: F401


@event.listens_for(Base.metadata, "after_create")
def _after_create(target: Any, connection: Any, **_kw: Any) -> None:  # pragma: no cover
    """Best-effort: in tests using `metadata.create_all` (rare; Alembic is canonical)."""
    return None


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
