"""LinkedIn Sign In with OpenID Connect — identity only.

Scopes: `openid profile email`. Endpoints per LinkedIn OIDC discovery:
  authorize: https://www.linkedin.com/oauth/v2/authorization
  token:     https://www.linkedin.com/oauth/v2/accessToken
  userinfo:  https://api.linkedin.com/v2/userinfo

Returns enough to sign the user in (sub, email, name, picture, locale). For
the full profile we need the DMA scope (separate flow).
"""
from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


LINKEDIN_AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"


def build_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    scopes: list[str] | None = None,
) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": " ".join(scopes or ["openid", "profile", "email"]),
    }
    return f"{LINKEDIN_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


async def exchange_code_for_token(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    """Exchange authorization code for token bundle.

    Response carries `access_token`, `expires_in`, `id_token`, `scope`.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            LINKEDIN_TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        r.raise_for_status()
        return r.json()


async def fetch_userinfo(access_token: str) -> dict[str, Any]:
    """Fetch the OIDC userinfo endpoint.

    Shape:
      {
        "sub": "abc123",
        "name": "Ada Lovelace",
        "given_name": "Ada",
        "family_name": "Lovelace",
        "picture": "https://...",
        "locale": {"country": "ES", "language": "es"},
        "email": "ada@example.com",
        "email_verified": true
      }
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            LINKEDIN_USERINFO_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        r.raise_for_status()
        return r.json()
