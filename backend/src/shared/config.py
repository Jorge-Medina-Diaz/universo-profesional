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

    env: Literal["development", "test", "production", "staging"] = "development"

    # In dev/test, mark new accounts as email-verified at registration time so
    # nobody has to fish through Mailhog or paste a link from the JSON response.
    # Production always requires real verification regardless of this flag.
    # Default is False (opt-in): if you want to skip verification in dev, set
    # AUTO_VERIFY_EMAILS_IN_DEV=true in your .env. This reduces the chance of a
    # production deploy accidentally bypassing email verification.
    auto_verify_emails_in_dev: bool = False

    # --- Database ---
    # Default is the dev compose URL. Production MUST override (validated in
    # `validate_production_ready` below).
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
    email_from_name: str = "Universo Profesional"
    email_provider: Literal["mock", "postmark", "brevo", "resend"] = "mock"
    brevo_api_key: str | None = None
    postmark_server_token: str | None = None
    resend_api_key: str | None = None

    # --- Storage ---
    storage_root: Path = Path("/app/var/documents")
    storage_provider: Literal["filesystem", "s3"] = "filesystem"
    # S3 (only used when storage_provider="s3"). endpoint_url lets you point at
    # MinIO / R2 / any S3-compatible store; leave None for AWS. Credentials may
    # also come from the ambient AWS chain (IAM role) — leave the keys None then.
    s3_bucket: str | None = None
    s3_region: str = "eu-west-1"
    s3_prefix: str = "documents"
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None

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
    stripe_api_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_premium_monthly: str | None = None
    stripe_price_pro_monthly: str | None = None
    stripe_success_url: str | None = None
    stripe_cancel_url: str | None = None
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
    # Defaults cover the local dev frontends: Vite (:5173), the baked prod
    # nginx image (:8080), and the occasional :3000. Production MUST still set
    # this explicitly via CORS_ORIGINS env as a JSON array, e.g.
    # CORS_ORIGINS=["https://app.universo.pro","https://www.universo.pro"]
    #
    # NOTE: the :8080 prod image is designed for SAME-ORIGIN use — nginx proxies
    # /api, /agui, /mcp to the backend, so the SPA should call RELATIVE URLs and
    # never actually trigger CORS. These entries are a belt-and-suspenders safety
    # net for any absolute-URL build (e.g. a stray VITE_API_BASE_URL).
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:3000",
    ]

    # --- Rate limiting ---
    rate_limit_enabled: bool = True
    rate_limit_storage_uri: str | None = None  # defaults to redis_url

    # --- Integrations (OAuth apps) ---
    github_client_id: str | None = None
    github_client_secret: str | None = None
    linkedin_client_id: str | None = None
    linkedin_client_secret: str | None = None
    linkedin_dma_enabled: bool = False
    # Bright Data: paid 3rd-party LinkedIn data provider (gated behind PRO).
    # Replaces the deprecated Proxycurl/NinjaPear pipeline. The dataset id
    # below is Bright Data's well-known LinkedIn People Profile collection;
    # override only if you build a custom one.
    brightdata_api_key: str | None = None
    brightdata_dataset_id: str = "gd_l1viktl72bvl7bjuj0"

    @property
    def agents_provider_resolved(self) -> str:
        """Pick the real provider when a key is set, else mock.

        Lets a dev set `ANTHROPIC_API_KEY` in `.env` and have agents go live
        without touching `AGENTS_PROVIDER` — convenient for local testing.
        """
        if self.agents_provider != "mock":
            return self.agents_provider
        if self.anthropic_api_key:
            return "anthropic"
        if self.openai_api_key:
            return "openai"
        return "mock"

    @property
    def llm_provider_resolved(self) -> str:
        """Same auto-detection for the structured-output LLM (PDF parsing,
        knowledge extraction). A single API key enables it without also
        having to flip LLM_PROVIDER — closes the "chat works but extraction
        stays mock" footgun.
        """
        if self.llm_provider != "mock":
            return self.llm_provider
        if self.anthropic_api_key:
            return "anthropic"
        if self.openai_api_key:
            return "openai"
        return "mock"

    @property
    def embeddings_provider_resolved(self) -> str:
        """Real embeddings require OpenAI (there's no Anthropic embeddings
        endpoint here). If the deterministic default is left but an OpenAI
        key exists, use OpenAI — otherwise semantic search / knowledge would
        silently run on non-semantic SHA-256 vectors.
        """
        if self.embeddings_provider != "deterministic":
            return self.embeddings_provider
        if self.openai_api_key:
            return "openai"
        return "deterministic"

    def provider_warnings(self) -> list[str]:
        """Non-blocking advisories about provider coherence, logged at startup.

        These don't stop the app (deterministic embeddings are a valid
        choice), but they surface the degraded-RAG footgun explicitly.
        """
        warnings: list[str] = []
        agents_real = self.agents_provider_resolved != "mock"
        if agents_real and self.embeddings_provider_resolved == "deterministic":
            warnings.append(
                "Agents use a real LLM but EMBEDDINGS_PROVIDER resolves to "
                "'deterministic' — semantic search, retrieval and knowledge "
                "ranking run on NON-semantic vectors. Set OPENAI_API_KEY for "
                "real embeddings."
            )
        if agents_real and self.llm_provider_resolved == "mock":
            warnings.append(
                "Agents use a real LLM but LLM_PROVIDER resolves to 'mock' — "
                "PDF parsing and knowledge entity-extraction will no-op."
            )
        return warnings

    # --- Token encryption ---
    token_encryption_key: str | None = None

    # --- Agents (Agno) ---
    # Coordinator does the routing — wants a strong reasoner. Specialists work
    # on small, focused payloads — cheap/fast model is fine. Both fall back to
    # a mock provider when no API key is configured so dev/tests run offline.
    agents_coordinator_model: str = "claude-sonnet-4-6"
    agents_specialist_model: str = "claude-haiku-4-5-20251001"
    agents_provider: Literal["mock", "anthropic", "openai"] = "mock"
    # The mock LLM serves deterministic, FABRICATED content. Fine for dev/test
    # but must never silently back a real user's CV/agent in prod. Defaults off;
    # dev/test envs are allowed via mock_llm_allowed.
    allow_mock_llm: bool = False
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    # R13 (experimental, default OFF): add ONE generalist `entity_curator` agent
    # — armed with a single generic `propose_entity(entity_type, payload)` tool —
    # ALONGSIDE the per-entity CRUD specialists. Lets us A/B consolidating the
    # routing surface before removing the per-entity specialists (a later step).
    # When OFF, the propose_entity tool is never registered, so its streaming
    # special-case and frontend action are unreachable: zero blast radius.
    agents_entity_curator_enabled: bool = False

    # --- Retrieval reranking (cross-encoder stage after RRF) ---
    # Retrieve a wider candidate pool cheaply (BM25+dense+PPR+RRF), then
    # rerank the top-N against the query for a precision lift. Default uses
    # an LLM listwise reranker on the existing Anthropic provider (no new
    # dependency/key); set RERANK_PROVIDER=cohere|voyage + RERANK_API_KEY to
    # use a hosted cross-encoder. RERANK_PROVIDER=none (or RERANK_ENABLED=false)
    # preserves the pure-RRF order.
    rerank_enabled: bool = True
    rerank_provider: Literal["llm", "cohere", "voyage", "none"] = "llm"
    rerank_api_key: str | None = None
    rerank_model: str | None = None  # provider-specific; LLM falls back to specialist model
    rerank_candidate_pool: int = 40

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
    def mock_llm_allowed(self) -> bool:
        return self.allow_mock_llm or self.is_dev or self.is_test

    def assert_llm_usable(self) -> None:
        """Raise if the resolved LLM/agents provider is 'mock' where it isn't
        allowed (prod without a key). Call at any mock-construction choke point
        so we never ship hallucinated content instead of a visible error."""
        if self.mock_llm_allowed:
            return
        if (
            self.agents_provider_resolved == "mock"
            or self.llm_provider_resolved == "mock"
        ):
            raise RuntimeError(
                "LLM provider resolved to 'mock' but mock is not allowed here — "
                "refusing to serve fabricated content. Configure ANTHROPIC_API_KEY "
                "or OPENAI_API_KEY (or set ALLOW_MOCK_LLM=true)."
            )

    @property
    def mcp_canonical_uri(self) -> str:
        return f"{self.canonical_base_url}/mcp"

    @property
    def alembic_url(self) -> str:
        if self.database_url_sync:
            return self.database_url_sync
        # Derive sync URL from async URL
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    # --- Insecure-default tokens we must never see in production ---
    _DEV_DB_URL_MARKER = "cvs_dev_password"

    def validate_production_ready(self) -> list[str]:
        """Return a list of validation errors when `env == production`.

        Empty list ⇒ all good. Non-empty ⇒ caller should refuse to start.

        We check that every secret/URL that has a dev-friendly default has been
        explicitly overridden, AND that the providers wired to "real" services
        actually have keys configured. We DELIBERATELY do not raise here so
        callers can collect every problem and report them all at once.
        """
        errors: list[str] = []
        if not self.is_prod:
            return errors

        # Core infra — these MUST be overridden from their dev defaults.
        if self._DEV_DB_URL_MARKER in self.database_url:
            errors.append("DATABASE_URL is the dev default; set a real Postgres URL")
        if self.canonical_base_url.startswith("http://localhost"):
            errors.append("CANONICAL_BASE_URL is localhost; set the public URL")
        if self.frontend_base_url.startswith("http://localhost"):
            errors.append("FRONTEND_BASE_URL is localhost; set the public URL")
        if not self.cors_origins or any(
            o.startswith("http://localhost") for o in self.cors_origins
        ):
            errors.append(
                "CORS_ORIGINS must be set to the production frontend URL(s)"
            )
        # Redis backs arq jobs, rate-limit counters + cached summaries. A prod
        # deploy left on the localhost default silently has no working queue /
        # shared rate limiting across replicas.
        _local_redis = ("redis://localhost", "redis://127.0.0.1")
        if self.redis_url.startswith(_local_redis):
            errors.append("REDIS_URL is the localhost default; set the production Redis URL")
        if self.rate_limit_storage_uri and self.rate_limit_storage_uri.startswith(
            (*_local_redis, "memory://")
        ):
            errors.append(
                "RATE_LIMIT_STORAGE_URI is localhost/in-memory; set a shared Redis URI "
                "so rate limits hold across replicas"
            )

        # Secrets.
        if not self.token_encryption_key:
            errors.append(
                "TOKEN_ENCRYPTION_KEY is required in production (Fernet key)"
            )

        # Email — must be a real provider, not mock.
        if self.email_provider == "mock":
            errors.append("EMAIL_PROVIDER must be 'brevo' or 'postmark' in production")
        if self.email_provider == "brevo" and not self.brevo_api_key:
            errors.append("BREVO_API_KEY is required when EMAIL_PROVIDER=brevo")
        if self.email_provider == "postmark" and not self.postmark_server_token:
            errors.append(
                "POSTMARK_SERVER_TOKEN is required when EMAIL_PROVIDER=postmark"
            )
        if self.email_from.endswith(".local"):
            errors.append("EMAIL_FROM still points to a .local domain")

        # LLM — must be Anthropic or OpenAI, not mock.
        if self.agents_provider == "mock" and not (
            self.anthropic_api_key or self.openai_api_key
        ):
            errors.append(
                "Configure ANTHROPIC_API_KEY or OPENAI_API_KEY (LLM provider falls back to mock otherwise)"
            )

        # Stripe — if billing is enabled, real keys + webhook secret required.
        if self.stripe_provider == "real":
            if not self.stripe_api_key:
                errors.append("STRIPE_API_KEY is required when STRIPE_PROVIDER=real")
            if not self.stripe_webhook_secret:
                errors.append(
                    "STRIPE_WEBHOOK_SECRET is required when STRIPE_PROVIDER=real"
                )
            if not self.stripe_price_premium_monthly:
                errors.append("STRIPE_PRICE_PREMIUM_MONTHLY price id missing")
            if not self.stripe_price_pro_monthly:
                errors.append("STRIPE_PRICE_PRO_MONTHLY price id missing")

        # JWT keys must exist on disk OR be derivable on first run.
        # (security.py auto-generates them into the volume on first start —
        # we just warn if the path is the dev default and nobody has mounted a
        # persistent volume.)
        if str(self.jwt_private_key_path) == "/app/var/keys/jwt_private.pem":
            # OK — that's the default expected mount path. Nothing to flag.
            pass

        # Dangerous flags that must never be true in prod.
        if self.auto_verify_emails_in_dev:
            errors.append(
                "AUTO_VERIFY_EMAILS_IN_DEV is set — disable in production"
            )
        if self.database_echo:
            errors.append("DATABASE_ECHO=true leaks SQL to logs — disable in production")

        return errors


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
