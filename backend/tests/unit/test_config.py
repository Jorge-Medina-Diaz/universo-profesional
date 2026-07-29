"""Unit tests for shared config properties."""
from __future__ import annotations

from src.shared.config import Settings


class TestSettings:
    def test_is_dev_test_prod(self):
        s = Settings(env="development")
        assert s.is_dev is True
        assert s.is_test is False
        assert s.is_prod is False

    def test_is_test(self):
        s = Settings(env="test")
        assert s.is_test is True

    def test_is_prod(self):
        s = Settings(env="production")
        assert s.is_prod is True

    def test_agents_provider_resolved_with_key(self):
        s = Settings(agents_provider="mock", anthropic_api_key="sk-test")
        assert s.agents_provider_resolved == "anthropic"

    def test_agents_provider_resolved_openai(self):
        s = Settings(agents_provider="mock", openai_api_key="sk-test")
        assert s.agents_provider_resolved == "openai"

    def test_llm_provider_resolved(self):
        s = Settings(llm_provider="mock", anthropic_api_key="sk-test")
        assert s.llm_provider_resolved == "anthropic"

    def test_embeddings_provider_resolved(self):
        s = Settings(embeddings_provider="deterministic", openai_api_key="sk-test")
        assert s.embeddings_provider_resolved == "openai"

    def test_mcp_canonical_uri(self):
        s = Settings(canonical_base_url="http://localhost:8000")
        assert s.mcp_canonical_uri == "http://localhost:8000/mcp"

    def test_alembic_url_derived(self):
        s = Settings(database_url="postgresql+asyncpg://user:pass@localhost/db")
        assert s.alembic_url == "postgresql://user:pass@localhost/db"

    def test_alembic_url_explicit(self):
        s = Settings(database_url="postgresql+asyncpg://user:pass@localhost/db", database_url_sync="postgresql://x/y")
        assert s.alembic_url == "postgresql://x/y"

    def test_provider_warnings(self):
        s = Settings(agents_provider="anthropic", anthropic_api_key="k", embeddings_provider="deterministic")
        warnings = s.provider_warnings()
        assert any("deterministic" in w for w in warnings)

    def test_validate_production_ready_empty_in_dev(self):
        s = Settings(env="development")
        assert s.validate_production_ready() == []

    def test_validate_production_ready_catches_issues(self):
        s = Settings(
            env="production",
            database_url="postgresql+asyncpg://cvs:cvs_dev_password@localhost/cvs",
            canonical_base_url="http://localhost:8000",
            frontend_base_url="http://localhost:5173",
            cors_origins=["http://localhost:5173"],
        )
        errors = s.validate_production_ready()
        assert any("DATABASE_URL" in e for e in errors)
        assert any("CANONICAL_BASE_URL" in e for e in errors)
        assert any("CORS_ORIGINS" in e for e in errors)
        assert any("TOKEN_ENCRYPTION_KEY" in e for e in errors)

    def test_validate_production_ready_email_mock(self):
        s = Settings(env="production", email_provider="mock")
        errors = s.validate_production_ready()
        assert any("EMAIL_PROVIDER" in e for e in errors)

    def test_validate_production_ready_stripe_real(self):
        s = Settings(env="production", stripe_provider="real")
        errors = s.validate_production_ready()
        assert any("STRIPE_API_KEY" in e for e in errors)
