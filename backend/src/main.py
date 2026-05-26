"""FastAPI application entrypoint — composition root.

Wires every bounded context's router, the MCP server subapp, the OAuth AS,
the well-known metadata, and the observability/middleware stack.
"""
from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi.errors import RateLimitExceeded
from starlette.responses import Response

from src.shared.config import get_settings
from src.shared.db import dispose_engine, import_all_models
from src.shared.errors import DomainError
from src.shared.events import get_event_bus
from src.shared.logging import configure_logging, get_logger
from src.shared.middleware import SecurityHeadersMiddleware
from src.shared.rate_limit import limiter, rate_limit_exceeded_handler
from src.shared.security import ensure_jwt_keys

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup + shutdown hooks."""
    configure_logging()
    settings = get_settings()
    logger.info("app_starting", env=settings.env, canonical=settings.canonical_base_url)

    # 0. Fail fast if the production config is missing critical secrets.
    config_errors = settings.validate_production_ready()
    if config_errors:
        for err in config_errors:
            logger.error("config_error", problem=err)
        raise RuntimeError(
            "Refusing to start in production with incomplete config:\n  - "
            + "\n  - ".join(config_errors)
        )

    # 0b. Non-blocking provider-coherence advisories (e.g. real LLM but
    # deterministic embeddings → degraded RAG). Logged so it's never silent.
    for warning in settings.provider_warnings():
        logger.warning("provider_advisory", problem=warning)
    logger.info(
        "providers_resolved",
        agents=settings.agents_provider_resolved,
        llm=settings.llm_provider_resolved,
        embeddings=settings.embeddings_provider_resolved,
    )

    # OpenTelemetry OTLP exporter
    try:
        from src.shared.otel_setup import init_otel

        init_otel()
    except Exception as exc:  # noqa: BLE001
        logger.warning("otel_init_failed", error=str(exc))

    # Optional Sentry — only initializes if SENTRY_DSN is set.
    try:
        from src.shared.sentry_setup import init_sentry

        init_sentry()
    except Exception as exc:  # noqa: BLE001
        logger.warning("sentry_init_failed", error=str(exc))

    # 1. Register ORM models (otherwise lazy-imports may miss tables)
    import_all_models()

    # 2. Ensure JWT keys exist (RSA 2048 generated on first run)
    ensure_jwt_keys()

    # 3. Wire event subscribers
    _wire_event_subscribers()

    yield

    logger.info("app_stopping")
    await dispose_engine()


def _wire_event_subscribers() -> None:
    """Subscribe in-process handlers to domain events."""
    from src.shared.activity_log import register as register_activity_log
    from src.universe.application.event_handlers import register_universe_subscribers

    bus = get_event_bus()
    register_universe_subscribers(bus)
    register_activity_log(bus)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Universo Profesional API",
        version="0.1.0",
        description=(
            "SaaS B2C de gestión integral del ciclo de vida profesional. "
            "REST API + Remote MCP server (OAuth 2.1 + PKCE + DCR)."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # --- Middleware --------------------------------------------------------
    # Order matters: rate limit BEFORE auth/handlers; security headers wraps
    # the response on the way out so it applies to errors too.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )

    # Rate limiting (slowapi). Limits applied per-route via `@limit(...)`
    # decorators in router files; the handler below renders 429s as JSON.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "request",
                method=request.method,
                path=request.url.path,
                duration_ms=round(elapsed_ms, 2),
            )
            structlog.contextvars.clear_contextvars()
        response.headers["X-Request-Id"] = request_id
        return response

    # --- Exception handlers ------------------------------------------------
    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content=exc.to_problem())

    # --- Routers -----------------------------------------------------------
    from src.billing.interfaces.api.router import router as billing_router
    from src.documents.interfaces.api.router import router as documents_router
    from src.documents.interfaces.api.router import public_router as documents_share_router
    from src.documents.interfaces.api.jobs_router import router as jobs_router
    from src.identity.interfaces.api.router import router as identity_router
    from src.identity.interfaces.api.users_router import router as users_router
    from src.mcp_server.interfaces.oauth_router import router as oauth_router
    from src.mcp_server.interfaces.well_known_router import router as well_known_router
    from src.mcp_server.interfaces.mcp_router import router as mcp_router
    from src.universe.interfaces.api.router import router as universe_router
    from src.universe.interfaces.api.import_router import router as import_router
    from src.universe.interfaces.api.goals_router import router as goals_router
    from src.universe.interfaces.api.shape_router import router as shape_router
    from src.shared.legal_router import router as legal_router

    app.include_router(identity_router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
    app.include_router(universe_router, prefix="/api/v1/universe", tags=["universe"])
    app.include_router(goals_router, prefix="/api/v1/goals", tags=["goals"])
    app.include_router(shape_router, prefix="/api/v1/universe/shape", tags=["universe"])
    app.include_router(import_router, prefix="/api/v1/import", tags=["import"])
    app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])
    app.include_router(documents_share_router, prefix="/api/v1/share", tags=["share"])
    app.include_router(jobs_router, prefix="/api/v1/jobs", tags=["jobs"])
    app.include_router(billing_router, prefix="/api/v1/billing", tags=["billing"])
    from src.integrations.interfaces.api.linkedin_oidc_router import (
        router as linkedin_oidc_router,
    )
    from src.integrations.interfaces.api.router import router as integrations_router

    app.include_router(integrations_router, prefix="/api/v1/integrations", tags=["integrations"])

    from src.notes.interfaces.api.router import router as notes_router

    app.include_router(notes_router, prefix="/api/v1/notes", tags=["notes"])

    from src.knowledge.interfaces.api.router import router as knowledge_router

    app.include_router(
        knowledge_router, prefix="/api/v1/knowledge", tags=["knowledge"]
    )
    app.include_router(
        linkedin_oidc_router,
        prefix="/api/v1/auth/linkedin",
        tags=["auth", "linkedin"],
    )
    app.include_router(oauth_router, prefix="/auth/oauth", tags=["oauth"])
    app.include_router(well_known_router, tags=["well-known"])
    app.include_router(mcp_router, prefix="/mcp", tags=["mcp"])
    app.include_router(legal_router, tags=["legal"])

    # Agents AG-UI streaming endpoint (chat-first frontend)
    from src.agents.interfaces.agui_router import router as agui_router
    from src.agents.interfaces.chat_sessions_router import router as chat_sessions_router

    app.include_router(agui_router, tags=["agui"])
    app.include_router(chat_sessions_router, prefix="/api/v1/chat", tags=["chat"])

    from src.coherence.interfaces.api.router import router as coherence_router

    app.include_router(coherence_router, prefix="/api/v1/coherence", tags=["coherence"])

    # Universe graph — Sprint M onwards (Apache AGE + ESCO).
    from src.graph.interfaces.api.graph_router import router as graph_router

    app.include_router(graph_router, tags=["graph"])

    # --- Health & metrics --------------------------------------------------
    @app.get("/health", tags=["health"])
    @app.get("/healthz", tags=["health"])
    async def health() -> dict[str, str]:
        """Liveness probe — the process is up. Doesn't check dependencies.

        Used by load balancers / Fly.io / Kubernetes to decide whether to
        restart the container. See `/readyz` for the dependency-aware check.
        """
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    async def readiness() -> JSONResponse:
        """Readiness probe — verifies the app can actually serve traffic.

        Checks DB, Redis, and JWT keys. Returns 503 + per-check status when
        any dependency is unavailable so load balancers can stop routing.

        Each check has its own short timeout (2s) so a slow dependency
        doesn't pile up.
        """
        import asyncio

        from src.shared.db import get_engine

        results: dict[str, str] = {}
        overall_ok = True

        # DB
        try:
            async def _ping_db() -> None:
                from sqlalchemy import text

                async with get_engine().connect() as conn:
                    await conn.execute(text("SELECT 1"))

            await asyncio.wait_for(_ping_db(), timeout=2.0)
            results["database"] = "ok"
        except Exception as exc:  # noqa: BLE001
            results["database"] = f"error: {exc}"
            overall_ok = False

        # Redis (best-effort — only enabled when worker queue is configured)
        try:
            from arq import create_pool
            from arq.connections import RedisSettings

            async def _ping_redis() -> None:
                pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
                try:
                    await pool.ping()  # type: ignore[attr-defined]
                except AttributeError:
                    # older arq exposes the underlying redis as .pool
                    pass
                finally:
                    pool.close()
                    await pool.wait_closed() if hasattr(pool, "wait_closed") else None

            await asyncio.wait_for(_ping_redis(), timeout=2.0)
            results["redis"] = "ok"
        except Exception as exc:  # noqa: BLE001
            results["redis"] = f"error: {exc}"
            overall_ok = False

        # JWT keys
        try:
            from src.shared.security import get_private_key, get_public_key

            get_private_key()
            get_public_key()
            results["jwt_keys"] = "ok"
        except Exception as exc:  # noqa: BLE001
            results["jwt_keys"] = f"error: {exc}"
            overall_ok = False

        # LLM provider — just configuration check, no network ping (would be
        # too slow + the provider has its own SLAs we shouldn't gate on).
        results["llm_provider"] = settings.agents_provider_resolved

        status_code = 200 if overall_ok else 503
        return JSONResponse(
            status_code=status_code,
            content={"status": "ok" if overall_ok else "degraded", "checks": results},
        )

    @app.get("/metrics", tags=["observability"])
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # OpenTelemetry instrumentation
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception as exc:  # noqa: BLE001
        logger.warning("otel_instrumentation_failed", error=str(exc))

    return app


app = create_app()
