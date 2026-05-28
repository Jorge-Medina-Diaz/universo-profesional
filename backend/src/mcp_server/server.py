"""MCP server using the official Python SDK with SSE transport.

The sub-app mounts two transports side-by-side:
  * Legacy JSON-RPC over HTTP at POST /
  * SDK-native SSE at GET /sse + POST /messages/

Auth is enforced on every request via the existing OAuth 2.1 Bearer tokens.
"""
from __future__ import annotations

import json
import time
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException
from jose import JWTError
from mcp.server import Server
from mcp.server.sse import SseServerTransport, TransportSecuritySettings
from mcp.types import TextContent, Tool
from starlette.requests import Request
from starlette.responses import Response

from src.mcp_server.infrastructure.oauth_store import OAuthStore
from src.mcp_server.interfaces.mcp_router import mcp_endpoint
from src.mcp_server.interfaces.mcp_router import router as legacy_router
from src.mcp_server.tools import _TOOL_SCOPES, TOOL_DEFINITIONS, TOOL_HANDLERS
from src.shared.config import get_settings
from src.shared.db import get_session_factory
from src.shared.metrics import mcp_invocations_total, mcp_latency_seconds
from src.shared.security import decode_jwt, utc_now

PROTOCOL_VERSION = "2025-11-25"
SERVER_INFO = {"name": "cvs-saas-mcp", "version": "0.2.0"}


async def _authenticate_token(
    authorization: str | None,
) -> tuple[UUID, UUID, list[str]] | None:
    """Validate a Bearer token and return (user_id, client_id, scopes)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    settings = get_settings()
    try:
        claims = decode_jwt(token, audience=settings.mcp_canonical_uri)
    except JWTError:
        return None

    factory = get_session_factory()
    async with factory() as session:
        store = OAuthStore(session)
        row = await store.get_token(token)
        if (
            row is None
            or row.kind != "access"
            or row.revoked_at is not None
            or row.expires_at < utc_now()
        ):
            return None
        try:
            user_id = UUID(claims["sub"])
            client_id = UUID(claims["client_id"])
        except (KeyError, ValueError):
            return None
        scopes = (claims.get("scope") or "").split()
        return user_id, client_id, scopes


def _www_authenticate() -> str:
    return (
        f'Bearer realm="cvs-saas-mcp", '
        f'resource_metadata="{get_settings().canonical_base_url}'
        f'/.well-known/oauth-protected-resource"'
    )


async def _require_auth(
    authorization: str | None = Header(None),
) -> tuple[UUID, UUID, list[str]]:
    """FastAPI dependency — raises 401 on invalid or missing token."""
    auth = await _authenticate_token(authorization)
    if auth is None:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": _www_authenticate()},
        )
    return auth


# ---------------------------------------------------------------------------
# SDK server factory
# ---------------------------------------------------------------------------


def _create_sdk_server() -> Server:
    server = Server(SERVER_INFO["name"])

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOL_DEFINITIONS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        start = time.perf_counter()
        ok = True
        error_code: str | None = None
        user_id: UUID | None = None
        client_id: UUID | None = None

        try:
            # Auth from request context (the POST request)
            req: Request = server.request_context.request
            auth_header = req.headers.get("authorization", "")
            auth = await _authenticate_token(auth_header)
            if auth is None:
                raise PermissionError("Unauthorized")

            user_id, client_id, scopes = auth

            # Scope check
            required = _TOOL_SCOPES.get(name)
            if required and required not in scopes:
                raise PermissionError(f"Missing required scope: {required}")

            handler = TOOL_HANDLERS.get(name)
            if handler is None:
                raise ValueError(f"Unknown tool: {name}")

            result = await handler(user_id=user_id, args=arguments)
            text = json.dumps(result, default=str)
            return [TextContent(type="text", text=text)]
        except Exception as exc:
            ok = False
            error_code = type(exc).__name__
            # Return as text so the client sees the error inline
            return [TextContent(type="text", text=json.dumps({"error": f"{error_code}: {exc}"}))]
        finally:
            latency = int((time.perf_counter() - start) * 1000)
            mcp_invocations_total.labels(tool=name or "unknown", ok=str(ok).lower()).inc()
            mcp_latency_seconds.labels(tool=name or "unknown").observe(latency / 1000.0)
            if user_id is not None:
                try:
                    factory = get_session_factory()
                    async with factory() as session:
                        store = OAuthStore(session)
                        await store.log_invocation(
                            user_id=user_id,
                            client_id=client_id,
                            tool_name=name or "unknown",
                            ok=ok,
                            latency_ms=latency,
                            error_code=error_code,
                        )
                        await session.commit()
                except Exception:
                    pass

    return server


# ---------------------------------------------------------------------------
# Custom ASGI responses for SSE
# ---------------------------------------------------------------------------


class _SSEResponse(Response):
    """ASGI response that runs the MCP server over an SSE stream."""

    def __init__(
        self,
        transport: SseServerTransport,
        server: Server,
        init_options: Any,
    ) -> None:
        super().__init__(content=None, status_code=200, media_type="text/event-stream")
        self._transport = transport
        self._server = server
        self._init_options = init_options

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        async with self._transport.connect_sse(scope, receive, send) as streams:
            await self._server.run(
                streams[0], streams[1], self._init_options, raise_exceptions=False
            )


class _MessagesResponse(Response):
    """ASGI response that forwards a POST body into the SSE transport."""

    def __init__(self, transport: SseServerTransport) -> None:
        super().__init__(content=None, status_code=200)
        self._transport = transport

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        await self._transport.handle_post_message(scope, receive, send)


# ---------------------------------------------------------------------------
# Sub-app factory
# ---------------------------------------------------------------------------


def create_mcp_app() -> FastAPI:
    """Return a FastAPI sub-app exposing legacy + SDK-native MCP transports."""
    app = FastAPI(
        title="MCP Server",
        description="Universo Profesional MCP — OAuth 2.1 + SSE + legacy JSON-RPC",
    )

    app.include_router(legacy_router, prefix="/jsonrpc", tags=["mcp-legacy"])

    # Also mount at root for backward compat (tests + old clients use /mcp)
    app.post("")(mcp_endpoint)
    app.post("/")(mcp_endpoint)

    # SDK-native SSE transport
    transport = SseServerTransport(
        "/messages/",
        security_settings=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    sdk_server = _create_sdk_server()
    init_options = sdk_server.create_initialization_options()

    @app.get("/sse")
    async def sse_endpoint(
        _auth: tuple[UUID, UUID, list[str]] = Depends(_require_auth),
    ) -> Response:
        return _SSEResponse(transport, sdk_server, init_options)

    @app.post("/messages/")
    async def messages_endpoint(
        _auth: tuple[UUID, UUID, list[str]] = Depends(_require_auth),
    ) -> Response:
        return _MessagesResponse(transport)

    return app
