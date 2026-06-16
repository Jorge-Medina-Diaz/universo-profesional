"""MCP server sub-app — canonical JSON-RPC-over-HTTP transport.

Auth (OAuth 2.1 Bearer), RLS, per-call quota, rate limiting and the tool
surface all live in ``interfaces/mcp_router.py``; this module only mounts that
endpoint as a sub-app. The MCP spec 2025-11-25 Streamable-HTTP transport is
implemented directly there for tight control over auth/RLS.
"""
from __future__ import annotations

from fastapi import FastAPI

from src.mcp_server.interfaces.mcp_router import mcp_endpoint


def create_mcp_app() -> FastAPI:
    """Return a FastAPI sub-app exposing the MCP JSON-RPC HTTP transport."""
    app = FastAPI(
        title="MCP Server",
        description="Universo Profesional MCP — OAuth 2.1 + JSON-RPC over HTTP",
    )
    # Mounted at /mcp by the main app; accept both /mcp and /mcp/.
    app.post("")(mcp_endpoint)
    app.post("/")(mcp_endpoint)
    return app
