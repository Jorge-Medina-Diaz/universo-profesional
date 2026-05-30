"""Rate limiting — global slowapi setup + per-route decorators.

We use `slowapi` (Flask-Limiter port for ASGI) backed by Redis so limits
survive process restarts and apply across worker replicas.

Two patterns are exposed:
  1. `limit("5/15minutes")` decorator on individual endpoints (preferred).
  2. The middleware itself does NOT apply a global default — we'd rather
     opt-in per route to avoid surprise 429s on health/metrics/AG-UI streams.

Limits are skipped when:
  * `RATE_LIMIT_ENABLED=false` (e.g. tests)
  * The request has `X-Forwarded-For` from a trusted internal IP (TBD,
    not used today).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.shared.config import get_settings


def _key_func(request: Request) -> str:
    """Identify a caller for rate-limit purposes.

    Prefer the JWT subject when the user is authenticated — that way two users
    behind the same NAT/proxy don't share a bucket. Falls back to the remote
    IP (slowapi's default) when no Authorization header is present.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        if token:
            # Key on the STABLE `sub` claim, not the token tail: the old
            # `token[-16:]` (signature tail) changed on every refresh/re-login,
            # so a caller could evade any per-user limit just by refreshing, and
            # 16 chars of signature is collision-prone. This is only a
            # partitioning key (auth is enforced downstream), so unverified
            # claims are fine and must never raise.
            import hashlib

            try:
                from jose import jwt as _jwt

                sub = _jwt.get_unverified_claims(token).get("sub")
                if sub:
                    return f"user:{sub}"
            except Exception:
                pass
            # Opaque/garbage token → stable per-token bucket (no collision).
            return f"jwt:{hashlib.sha256(token.encode()).hexdigest()[:32]}"
    return get_remote_address(request)


def _build_limiter() -> Limiter:
    settings = get_settings()
    storage_uri = settings.rate_limit_storage_uri or settings.redis_url
    return Limiter(
        key_func=_key_func,
        storage_uri=storage_uri,
        enabled=settings.rate_limit_enabled,
        # `headers_enabled=True` would require every limited endpoint to
        # accept a `response: Response` param so slowapi can inject the
        # X-RateLimit-* headers. We disable injection and surface the
        # retry-after via our 429 exception handler instead — cleaner and
        # doesn't leak the limiter into the public signatures.
        headers_enabled=False,
    )


# Singleton — `limit()` reads it on each call so swap-out in tests is fine.
limiter: Limiter = _build_limiter()


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Translate slowapi's exception into our problem-detail JSON shape."""
    retry_after = getattr(exc, "retry_after", None)
    headers: dict[str, str] = {}
    if retry_after:
        headers["Retry-After"] = str(int(retry_after))
    return JSONResponse(
        status_code=429,
        content={
            "title": "Too many requests",
            "detail": str(exc.detail) if getattr(exc, "detail", None) else "rate_limit_exceeded",
            "retry_after_seconds": retry_after,
        },
        headers=headers,
    )


def limit(rule: str) -> Callable[[Any], Any]:
    """Decorator shortcut — `@limit("5/15minutes")`.

    Kept thin so route files don't need to import slowapi directly.
    """
    return limiter.limit(rule)
