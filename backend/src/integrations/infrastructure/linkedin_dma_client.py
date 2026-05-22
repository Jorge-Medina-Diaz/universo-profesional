"""LinkedIn DMA (Member Data Portability) 3rd-Party API client.

Status: requires LinkedIn approval (Company Page + super-admin + verification).
Until that's wired the call paths exist but the `fetch_member_snapshot` call is
gated behind `LINKEDIN_DMA_ENABLED`. With the flag off, a deterministic mock
fixture is returned — same shape as the real response — so the rest of the
pipeline (mapping, import sessions, UI) is exercised in dev.

Endpoint reference (subject to LinkedIn changing it; check
https://learn.microsoft.com/en-us/linkedin/dma/concepts/member-data-portability
before relying on it):

  GET https://api.linkedin.com/rest/memberSnapshotData?q=criteria&domain=PROFILE
  Headers:
    Authorization: Bearer <access_token>
    LinkedIn-Version: 202401
    X-Restli-Protocol-Version: 2.0.0

Each `domain` returns a list of elements. We aggregate domains:
  PROFILE, POSITIONS, EDUCATION, SKILLS, LANGUAGES, CERTIFICATIONS,
  HONORS, PUBLICATIONS, PATENTS, PROJECTS, COURSES, VOLUNTEERING_EXPERIENCE.

The DMA OAuth scope is `r_dma_portability_3rd_party` — different from OIDC's
`openid profile email` set, so an OIDC-only user still has to authorize the
DMA scope separately (which is what we expose at /authorize-dma).
"""
from __future__ import annotations

import asyncio
import urllib.parse
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


LINKEDIN_AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_DMA_BASE = "https://api.linkedin.com/rest"
LINKEDIN_API_VERSION = "202401"

DMA_SCOPE = "r_dma_portability_3rd_party"

# Domains we pull. Names mirror what the snapshot API returns.
DOMAINS = (
    "PROFILE",
    "POSITIONS",
    "EDUCATION",
    "SKILLS",
    "LANGUAGES",
    "CERTIFICATIONS",
    "HONORS",
    "PUBLICATIONS",
    "PATENTS",
    "PROJECTS",
    "COURSES",
    "VOLUNTEERING_EXPERIENCE",
)


def build_dma_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    extra_scopes: list[str] | None = None,
) -> str:
    """LinkedIn OAuth authorize URL for the DMA scope.

    Often called *after* the OIDC sign-in, so the user is already logged into
    LinkedIn. The page will prompt for consent on the data-portability scope.
    """
    scopes = [DMA_SCOPE] + list(extra_scopes or [])
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": " ".join(scopes),
    }
    return f"{LINKEDIN_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


async def exchange_dma_code_for_token(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
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


async def fetch_member_snapshot(
    *,
    access_token: str,
    domain: str,
) -> list[dict[str, Any]]:
    """Pull all elements of a single domain.

    The real API is paginated via `start`/`count` query params. We iterate
    until empty.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": LINKEDIN_API_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
        "Accept": "application/json",
    }
    out: list[dict[str, Any]] = []
    start = 0
    page_size = 50
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            r = await client.get(
                f"{LINKEDIN_DMA_BASE}/memberSnapshotData",
                headers=headers,
                params={
                    "q": "criteria",
                    "domain": domain,
                    "start": start,
                    "count": page_size,
                },
            )
            r.raise_for_status()
            data = r.json()
            elements = data.get("elements") or []
            if not elements:
                break
            # Each element wraps its own data list in the DMA shape
            for el in elements:
                inner = el.get("snapshotData") or []
                out.extend(inner)
            paging = data.get("paging") or {}
            total = paging.get("total")
            start += page_size
            if total is not None and start >= total:
                break
            if start > 5000:  # safety net
                logger.warning("dma_fetch_runaway", domain=domain)
                break
    return out


async def fetch_all_domains(access_token: str) -> dict[str, list[dict[str, Any]]]:
    """Pull every supported domain in parallel.

    Returns `{domain: [elements, ...]}`. Domains that 403/404 are skipped with
    a warning, not raised, so a partial profile is better than nothing.
    """
    async def _safe(domain: str) -> tuple[str, list[dict[str, Any]]]:
        try:
            return domain, await fetch_member_snapshot(
                access_token=access_token, domain=domain
            )
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "dma_domain_failed",
                domain=domain,
                status=exc.response.status_code,
                detail=exc.response.text[:200],
            )
            return domain, []

    results = await asyncio.gather(*[_safe(d) for d in DOMAINS])
    return dict(results)
