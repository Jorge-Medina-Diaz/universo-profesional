"""Bright Data LinkedIn People Profile client.

Bright Data offers a synchronous "scrape" endpoint for their well-known
LinkedIn People Profile dataset (`gd_l1viktl72bvl7bjuj0`, ~115M profiles).
Unlike Proxycurl/NinjaPear (sunset May 2026), Bright Data has been around
for 10+ years and is the most stable B2B data provider in the market.

Endpoint shape:
  POST https://api.brightdata.com/datasets/v3/scrape
    ?dataset_id=gd_l1viktl72bvl7bjuj0
    &include_errors=true
  Headers:
    Authorization: Bearer <api_key>
    Content-Type: application/json
  Body: { "input": [{"url": "https://www.linkedin.com/in/<username>/"}] }

Response: array of profile objects, each with `experience[]`, `education[]`,
`skills[]`, `certifications[]`, `languages[]`, `courses[]`, `honors_and_awards[]`,
`publications[]`, `patents[]`, `projects[]`, `volunteer_experience[]`,
`recommendations[]`, plus identity (`name`, `first_name`, `headline`, `about`,
`current_company`, `position`, `city`, `country_code`, ...).

Latency: 30-90 s for a fresh lookup (Bright Data fetches LinkedIn live);
near-instant for cached profiles. Timeout: 180 s.
"""
from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


BRIGHTDATA_BASE = "https://api.brightdata.com"
BRIGHTDATA_SCRAPE_PATH = "/datasets/v3/scrape"


class BrightDataError(Exception):
    """Wraps Bright Data HTTP errors so the use case can react."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"BrightData {status}: {detail}")
        self.status = status
        self.detail = detail


def normalize_linkedin_url(raw: str) -> str:
    """Coerce a user-typed LinkedIn URL into Bright Data's expected shape.

    Bright Data accepts the canonical /in/<username>/ form. We trim
    trailing query params, force https, and ensure a single trailing slash.
    """
    s = raw.strip()
    if not s:
        return s
    # Drop query/fragment
    s = s.split("?", 1)[0].split("#", 1)[0]
    # Force https
    if s.startswith("http://"):
        s = "https://" + s[7:]
    if not s.startswith("https://"):
        s = "https://" + s
    # Ensure trailing slash
    if not s.endswith("/"):
        s += "/"
    return s


async def scrape_profile(
    *,
    api_key: str,
    dataset_id: str,
    linkedin_url: str,
    timeout_seconds: float = 180.0,
) -> dict[str, Any]:
    """Trigger a synchronous scrape and return the first profile in the response.

    Bright Data's /scrape endpoint blocks until the data is ready (caches when
    possible, fresh-fetches otherwise). We pass a single URL per call because
    we only ever look up one user at a time.
    """
    url = normalize_linkedin_url(linkedin_url)
    if not url or "linkedin.com/in/" not in url:
        raise BrightDataError(400, f"Invalid LinkedIn profile URL: {linkedin_url!r}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"input": [{"url": url}]}
    params = {"dataset_id": dataset_id, "include_errors": "true"}

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        r = await client.post(
            BRIGHTDATA_BASE + BRIGHTDATA_SCRAPE_PATH,
            headers=headers,
            params=params,
            json=payload,
        )
        if r.status_code >= 400:
            raise BrightDataError(r.status_code, r.text[:500])
        try:
            data = r.json()
        except Exception as exc:
            raise BrightDataError(r.status_code, f"Non-JSON response: {exc}") from exc

    # Bright Data's /scrape returns shape that varies by input cardinality:
    #   - Single URL  → bare object `{...profile fields...}`
    #   - Multiple URLs → `[{...}, {...}]`
    # Normalize both to a single profile dict.
    if isinstance(data, list):
        if not data:
            raise BrightDataError(502, "Empty array response")
        profile = data[0]
    elif isinstance(data, dict):
        profile = data
    else:
        raise BrightDataError(502, f"Unexpected response type: {type(data).__name__}")

    # Bright Data returns `{ "warning": "..." }` or `{ "error": "..." }` when
    # the profile is private / not found. Surface those as proper errors so
    # the use case can show a clear message.
    if isinstance(profile, dict) and profile.get("error"):
        raise BrightDataError(404, str(profile.get("error"))[:200])
    if not isinstance(profile, dict) or not (profile.get("name") or profile.get("first_name")):
        raise BrightDataError(
            404,
            f"Profile not retrievable (private or removed): {str(profile)[:200]}",
        )
    return profile


# ---------------------------------------------------------------------------
# Wire module-level ports so application layer stays import-clean.
# ---------------------------------------------------------------------------

from src.integrations.application.ports import linkedin_brightdata as _port  # noqa: E402

_port.scrape_profile = scrape_profile
