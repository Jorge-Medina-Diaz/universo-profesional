"""Application configuration loaded from environment variables.

Single source of truth — every module imports `get_settings()`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    env: Literal["development", "test", "production"] = "development"

    # --- Database ---
    database_url: str = Field(
        default="postgresql+asyncpg://cvs:cvs_dev_password@localhost:5432/cvs",
        description="Async SQLAlchemy URL (asyncpg driver)",
    )
    database_url_sync: str | None = Field(
        default=None,
        description="Sync URL for Alembic; derived from async URL if not set",
    )
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 5

    # --- Redis / Queue ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Email (mock = mailhog) ---
    email_host: str = "localhost"
    email_port: int = 1025
    email_from: str = "no-reply@cvs-saas.local"
    email_provider: Literal["mock", "postmark", "brevo"] = "mock"

    # --- Storage ---
    storage_root: Path = Path("/app/var/documents")
    storage_provider: Literal["filesystem", "s3"] = "filesystem"

    # --- JWT keys ---
    jwt_private_key_path: Path = Path("/app/var/keys/jwt_private.pem")
    jwt_public_key_path: Path = Path("/app/var/keys/jwt_public.pem")
    jwt_algorithm: str = "RS256"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 30
    jwt_oauth_access_ttl_minutes: int = 60  # MCP OAuth tokens — longer-lived per spec
    jwt_oauth_refresh_ttl_days: int = 90

    # --- URLs ---
    canonical_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:5173"

    # --- Providers (all mocked by default) ---
    llm_provider: Literal["mock", "anthropic", "openai", "mistral"] = "mock"
    embeddings_provider: Literal["deterministic", "openai", "mistral"] = "deterministic"
    stripe_provider: Literal["mock", "real"] = "mock"
    pdf_parser_provider: Literal["mock", "affinda"] = "mock"
    scraper_enabled: bool = False

    # --- Quotas (Free plan) ---
    free_cv_per_month: int = 3
    free_cover_letters_per_month: int = 1

    # --- MCP rate limiting ---
    mcp_rate_limit_per_minute: int = 100
    mcp_rate_limit_per_hour: int = 1000
    mcp_rate_limit_per_day: int = 10000

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:5173"]

    # --- Observability ---
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    sentry_dsn: str | None = None

    @property
    def is_dev(self) -> bool:
        return self.env == "development"

    @property
    def is_test(self) -> bool:
        return self.env == "test"

    @property
    def is_prod(self) -> bool:
        return self.env == "production"

    @property
    def mcp_canonical_uri(self) -> str:
        return f"{self.canonical_base_url}/mcp"

    @property
    def alembic_url(self) -> str:
        if self.database_url_sync:
            return self.database_url_sync
        # Derive sync URL from async URL
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
