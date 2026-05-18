"""Alembic environment — async-aware, reads DATABASE_URL_SYNC for offline mode."""
from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Ensure /app is on PYTHONPATH so we can import src.* models
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.shared.db import Base  # noqa: E402  (after sys.path tweak)
from src.shared.db import import_all_models  # noqa: E402

# Force-import all SQLAlchemy models so Alembic's autogenerate sees them.
import_all_models()

config = context.config

# Override sqlalchemy.url from env if present (compose passes asyncpg URL;
# alembic needs the sync URL — we use psycopg v3, scheme `postgresql+psycopg://`).
db_url_sync = os.getenv("DATABASE_URL_SYNC")
db_url_async = os.getenv("DATABASE_URL")
if db_url_sync:
    if db_url_sync.startswith("postgresql://"):
        db_url_sync = db_url_sync.replace("postgresql://", "postgresql+psycopg://", 1)
    config.set_main_option("sqlalchemy.url", db_url_sync)
elif db_url_async and db_url_async.startswith("postgresql+asyncpg://"):
    config.set_main_option(
        "sqlalchemy.url",
        db_url_async.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1),
    )

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    async_url = db_url_async or config.get_main_option("sqlalchemy.url")
    cfg = config.get_section(config.config_ini_section, {}) or {}
    cfg["sqlalchemy.url"] = async_url
    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url") or ""
    if "asyncpg" in url:
        asyncio.run(run_async_migrations())
    else:
        from sqlalchemy import engine_from_config

        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}) or {},
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
