"""Unit tests: production configuration validation."""
from __future__ import annotations

from src.shared.config import Settings


class TestValidateProductionReady:
    def test_empty_errors_in_dev(self) -> None:
        s = Settings(env="development")
        assert s.validate_production_ready() == []

    def test_rejects_localhost_cors(self) -> None:
        s = Settings(
            env="production",
            database_url="postgresql+asyncpg://u:p@db:5432/cvs",
            canonical_base_url="https://api.example.com",
            frontend_base_url="https://app.example.com",
            cors_origins=["http://localhost:5173"],
            token_encryption_key="test" * 8,
            email_provider="brevo",
            brevo_api_key="key",
        )
        errs = s.validate_production_ready()
        assert any("CORS_ORIGINS" in e for e in errs)

    def test_rejects_dev_db_url(self) -> None:
        s = Settings(
            env="production",
            database_url="postgresql+asyncpg://cvs:cvs_dev_password@localhost:5432/cvs",
            canonical_base_url="https://api.example.com",
            frontend_base_url="https://app.example.com",
            cors_origins=["https://app.example.com"],
            token_encryption_key="test" * 8,
            email_provider="brevo",
            brevo_api_key="key",
        )
        errs = s.validate_production_ready()
        assert any("DATABASE_URL" in e for e in errs)

    def test_rejects_mock_email_in_prod(self) -> None:
        s = Settings(
            env="production",
            database_url="postgresql+asyncpg://u:p@db:5432/cvs",
            canonical_base_url="https://api.example.com",
            frontend_base_url="https://app.example.com",
            cors_origins=["https://app.example.com"],
            token_encryption_key="test" * 8,
            email_provider="mock",
        )
        errs = s.validate_production_ready()
        assert any("EMAIL_PROVIDER" in e for e in errs)

    def test_rejects_localhost_redis(self) -> None:
        s = Settings(
            env="production",
            database_url="postgresql+asyncpg://u:p@db:5432/cvs",
            canonical_base_url="https://api.example.com",
            frontend_base_url="https://app.example.com",
            cors_origins=["https://app.example.com"],
            token_encryption_key="test" * 8,
            email_provider="brevo",
            brevo_api_key="key",
            redis_url="redis://localhost:6379/0",
        )
        errs = s.validate_production_ready()
        assert any("REDIS_URL" in e for e in errs)

    def test_rejects_in_memory_rate_limit_storage(self) -> None:
        s = Settings(
            env="production",
            database_url="postgresql+asyncpg://u:p@db:5432/cvs",
            canonical_base_url="https://api.example.com",
            frontend_base_url="https://app.example.com",
            cors_origins=["https://app.example.com"],
            token_encryption_key="test" * 8,
            email_provider="brevo",
            brevo_api_key="key",
            redis_url="redis://prod-redis:6379/0",
            rate_limit_storage_uri="memory://",
        )
        errs = s.validate_production_ready()
        assert any("RATE_LIMIT_STORAGE_URI" in e for e in errs)

    def test_accepts_valid_prod_config(self) -> None:
        s = Settings(
            env="production",
            database_url="postgresql+asyncpg://u:p@db:5432/cvs",
            canonical_base_url="https://api.example.com",
            frontend_base_url="https://app.example.com",
            cors_origins=["https://app.example.com"],
            token_encryption_key="test" * 8,
            email_provider="brevo",
            brevo_api_key="key",
            email_from="no-reply@example.com",
            anthropic_api_key="ak-test",
            redis_url="redis://prod-redis:6379/0",
        )
        errs = s.validate_production_ready()
        assert errs == []

    def test_rejects_auto_verify_in_prod(self) -> None:
        s = Settings(
            env="production",
            database_url="postgresql+asyncpg://u:p@db:5432/cvs",
            canonical_base_url="https://api.example.com",
            frontend_base_url="https://app.example.com",
            cors_origins=["https://app.example.com"],
            token_encryption_key="test" * 8,
            email_provider="brevo",
            brevo_api_key="key",
            auto_verify_emails_in_dev=True,
        )
        errs = s.validate_production_ready()
        assert any("AUTO_VERIFY_EMAILS_IN_DEV" in e for e in errs)

    def test_rejects_database_echo_in_prod(self) -> None:
        s = Settings(
            env="production",
            database_url="postgresql+asyncpg://u:p@db:5432/cvs",
            canonical_base_url="https://api.example.com",
            frontend_base_url="https://app.example.com",
            cors_origins=["https://app.example.com"],
            token_encryption_key="test" * 8,
            email_provider="brevo",
            brevo_api_key="key",
            database_echo=True,
        )
        errs = s.validate_production_ready()
        assert any("DATABASE_ECHO" in e for e in errs)
