"""RFC 8414 / RFC 9728 / SEP-1649 metadata endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.mcp_server.domain.scopes import SCOPES
from src.shared.config import get_settings
from src.shared.security import get_jwks

router = APIRouter()


@router.get("/.well-known/oauth-authorization-server")
async def authorization_server_metadata() -> dict[str, Any]:
    """RFC 8414 — OAuth 2.0 Authorization Server Metadata."""
    s = get_settings()
    base = s.canonical_base_url
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}/auth/oauth/authorize",
        "token_endpoint": f"{base}/auth/oauth/token",
        "registration_endpoint": f"{base}/auth/oauth/register",
        "revocation_endpoint": f"{base}/auth/oauth/revoke",
        "jwks_uri": f"{base}/.well-known/jwks.json",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": list(SCOPES.keys()),
        "service_documentation": f"{base}/docs",
        "resource_indicators_supported": True,
    }


@router.get("/.well-known/oauth-protected-resource")
async def protected_resource_metadata() -> dict[str, Any]:
    """RFC 9728 — OAuth 2.0 Protected Resource Metadata."""
    s = get_settings()
    base = s.canonical_base_url
    return {
        "resource": s.mcp_canonical_uri,
        "authorization_servers": [base],
        "bearer_methods_supported": ["header"],
        "scopes_supported": list(SCOPES.keys()),
        "resource_documentation": f"{base}/docs",
    }


@router.get("/.well-known/mcp/server-card.json")
async def mcp_server_card() -> dict[str, Any]:
    """SEP-1649 — MCP server card."""
    s = get_settings()
    base = s.canonical_base_url
    return {
        "name": "Universo Profesional",
        "version": "0.1.0",
        "description": (
            "Tu universo profesional, vivo y al servicio de tu carrera, "
            "accesible desde cualquier agente de IA, alojado en Europa y bajo tu control."
        ),
        "vendor": "cvs-saas (jorge@webtools.es)",
        "transport": {"type": "streamable-http", "url": f"{base}/mcp"},
        "authorization": {
            "type": "oauth2.1",
            "authorization_server": base,
            "metadata": f"{base}/.well-known/oauth-authorization-server",
            "resource_metadata": f"{base}/.well-known/oauth-protected-resource",
            "scopes": [
                {"name": k, "description": v.description, "destructive": v.destructive}
                for k, v in SCOPES.items()
            ],
        },
        "tools_overview": [
            {"name": "get_profile", "description": "Read your professional universe"},
            {"name": "get_universe_summary", "description": "Compact summary"},
            {"name": "add_education", "description": "Add an education entry"},
            {"name": "update_education", "description": "Patch an education entry"},
            {"name": "add_experience", "description": "Add a work experience"},
            {"name": "add_skill", "description": "Add a skill"},
            {"name": "match_job_to_profile", "description": "Score JD ↔ profile"},
            {"name": "generate_cv", "description": "Generate adapted CV"},
        ],
    }


@router.get("/.well-known/jwks.json")
async def jwks() -> dict[str, Any]:
    return get_jwks()
