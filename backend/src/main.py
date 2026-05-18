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
from starlette.responses import Response

from src.shared.config import get_settings
from src.shared.db import dispose_engine, import_all_models
from src.shared.errors import DomainError
from src.shared.events import get_event_bus
from src.shared.logging import configure_logging, get_logger
from src.shared.security import ensure_jwt_keys

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup + shutdown hooks."""
    configure_logging()
    settings = get_settings()
    logger.info("app_starting", env=settings.env, canonical=settings.canonical_base_url)

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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )

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
    from src.identity.interfaces.api.router import router as identity_router
    from src.identity.interfaces.api.users_router import router as users_router
    from src.mcp_server.interfaces.oauth_router import router as oauth_router
    from src.mcp_server.interfaces.well_known_router import router as well_known_router
    from src.mcp_server.interfaces.mcp_router import router as mcp_router
    from src.universe.interfaces.api.router import router as universe_router
    from src.universe.interfaces.api.import_router import router as import_router
    from src.shared.legal_router import router as legal_router

    app.include_router(identity_router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
    app.include_router(universe_router, prefix="/api/v1/universe", tags=["universe"])
    app.include_router(import_router, prefix="/api/v1/import", tags=["import"])
    app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])
    app.include_router(billing_router, prefix="/api/v1/billing", tags=["billing"])
    from src.integrations.interfaces.api.router import router as integrations_router

    app.include_router(integrations_router, prefix="/api/v1/integrations", tags=["integrations"])
    app.include_router(oauth_router, prefix="/auth/oauth", tags=["oauth"])
    app.include_router(well_known_router, tags=["well-known"])
    app.include_router(mcp_router, prefix="/mcp", tags=["mcp"])
    app.include_router(legal_router, tags=["legal"])

    # --- Health & metrics --------------------------------------------------
    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

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
