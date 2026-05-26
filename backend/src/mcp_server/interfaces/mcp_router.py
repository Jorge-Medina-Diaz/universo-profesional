"""MCP Streamable HTTP transport.

We implement the JSON-RPC over HTTP transport defined in MCP spec 2025-11-25
directly (rather than embedding the full SDK subapp) so we have tight control
over auth, RLS and rate limiting. The protocol surface here covers:
  initialize, tools/list, tools/call, resources/list, resources/read

Auth: every request must carry `Authorization: Bearer <jwt>` with audience =
`<canonical>/mcp`. On 401 we return `WWW-Authenticate: Bearer
resource_metadata="…"` to point the client at the resource metadata.
"""
from __future__ import annotations

import json
import time
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from jose import JWTError

from src.identity.interfaces.api.deps import SessionDep
from src.mcp_server.application.tools import TOOLS
from src.mcp_server.infrastructure.oauth_store import OAuthStore
from src.shared.config import get_settings
from src.shared.db import set_rls_user
from src.shared.security import decode_jwt, utc_now

router = APIRouter()


PROTOCOL_VERSION = "2025-11-25"
SERVER_INFO = {"name": "cvs-saas-mcp", "version": "0.1.0"}


def _err_response(*, code: int, message: str, request_id: Any = None) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _ok_response(*, result: Any, request_id: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _www_authenticate() -> str:
    return (
        f'Bearer realm="cvs-saas-mcp", '
        f'resource_metadata="{get_settings().canonical_base_url}'
        f'/.well-known/oauth-protected-resource"'
    )


async def _authenticate(
    authorization: str | None, session: Any
) -> tuple[UUID, UUID, list[str]] | None:
    """Return (user_id, client_id, scopes) or None."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    settings = get_settings()
    try:
        claims = decode_jwt(token, audience=settings.mcp_canonical_uri)
    except JWTError:
        return None
    # Lookup token row to ensure not revoked and check expiry
    store = OAuthStore(session)
    row = await store.get_token(token)
    if row is None or row.kind != "access":
        return None
    if row.revoked_at is not None:
        return None
    if row.expires_at < utc_now():
        return None
    try:
        user_id = UUID(claims["sub"])
        client_id = UUID(claims["client_id"])
    except (KeyError, ValueError):
        return None
    scopes = (claims.get("scope") or "").split()
    return user_id, client_id, scopes


@router.api_route("", methods=["POST"])
@router.api_route("/", methods=["POST"])
async def mcp_endpoint(
    request: Request,
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    auth = await _authenticate(authorization, session)
    if auth is None:
        return JSONResponse(
            content=_err_response(code=-32001, message="Unauthorized"),
            status_code=401,
            headers={"WWW-Authenticate": _www_authenticate()},
        )
    user_id, client_id, scopes = auth
    await set_rls_user(session, user_id)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse(_err_response(code=-32700, message="Parse error"), status_code=400)

    method = body.get("method")
    params = body.get("params", {}) or {}
    rpc_id = body.get("id")

    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"listChanged": False, "subscribe": False},
                "prompts": {"listChanged": False},
                "logging": {},
            },
            "serverInfo": SERVER_INFO,
        }
        return JSONResponse(_ok_response(result=result, request_id=rpc_id))

    if method == "notifications/initialized":
        return JSONResponse({"jsonrpc": "2.0"}, status_code=202)

    if method == "tools/list":
        tools_list = [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema,
            }
            for t in TOOLS.values()
        ]
        return JSONResponse(_ok_response(result={"tools": tools_list}, request_id=rpc_id))

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {}) or {}
        tool = TOOLS.get(name)
        if tool is None:
            return JSONResponse(
                _err_response(code=-32602, message=f"Unknown tool: {name}", request_id=rpc_id)
            )
        # Scope check
        if tool.required_scope and tool.required_scope not in scopes:
            return JSONResponse(
                _err_response(
                    code=-32002,
                    message=f"Missing required scope: {tool.required_scope}",
                    request_id=rpc_id,
                ),
                status_code=403,
            )
        start = time.perf_counter()
        ok = True
        error_code = None
        try:
            result = await tool.handler(
                session=session, user_id=user_id, client_id=client_id, args=args
            )
            payload = {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}
            await session.commit()
            return JSONResponse(_ok_response(result=payload, request_id=rpc_id))
        except Exception as exc:
            ok = False
            error_code = type(exc).__name__
            return JSONResponse(
                _err_response(code=-32000, message=f"{error_code}: {exc}", request_id=rpc_id),
                status_code=500,
            )
        finally:
            latency = int((time.perf_counter() - start) * 1000)
            mcp_invocations_total.labels(
                tool=name or "unknown", ok=str(ok).lower()
            ).inc()
            mcp_latency_seconds.labels(tool=name or "unknown").observe(
                latency / 1000.0
            )
            try:
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

    if method == "resources/list":
        from src.mcp_server.application.resources import RESOURCES

        return JSONResponse(
            _ok_response(result={"resources": list(RESOURCES.values())}, request_id=rpc_id)
        )

    if method == "resources/read":
        from src.mcp_server.application.resources import read_resource

        uri = params.get("uri")
        content = await read_resource(session, user_id, uri or "")
        return JSONResponse(
            _ok_response(
                result={
                    "contents": [
                        {"uri": uri, "mimeType": "application/json", "text": json.dumps(content, default=str)}
                    ]
                },
                request_id=rpc_id,
            )
        )

    if method == "ping":
        return JSONResponse(_ok_response(result={}, request_id=rpc_id))

    return JSONResponse(
        _err_response(code=-32601, message=f"Method not found: {method}", request_id=rpc_id),
        status_code=404,
    )
