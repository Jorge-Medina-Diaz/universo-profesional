"""Shared HTTP middleware — security headers, rate-limit error handler, etc.

Mounted from `main.py`. Each middleware is small and side-effect-free so we
can compose them deterministically.
"""
from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# Default Content-Security-Policy. Tight by default; opens just what we need:
#   - Anthropic API (multimodal endpoint may proxy through us, but the
#     frontend talks to /agui not to api.anthropic.com directly — connect-src
#     is conservative so we don't accidentally allow exfiltration sinks)
#   - Stripe checkout + JS SDK (in case we add stripe.js for in-app payment
#     forms later — today we redirect to hosted checkout so we don't need it)
#   - Brevo: emails are sent server-side, no JS needed on the frontend
#   - Sentry: only if SENTRY_DSN is configured; the frontend SDK posts to
#     <ingest>.sentry.io. We add *.sentry.io to connect-src defensively.
_CSP_DIRECTIVES = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://js.stripe.com; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: https:; "
    "font-src 'self' data:; "
    "connect-src 'self' https://*.sentry.io https://api.stripe.com; "
    "frame-src 'self' https://js.stripe.com https://checkout.stripe.com; "
    "frame-ancestors 'none'; "
    "form-action 'self' https://checkout.stripe.com; "
    "base-uri 'self'; "
    "object-src 'none'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard hardening headers to every response.

    Headers chosen per OWASP secure-headers project recommendations:
      * Content-Security-Policy — XSS / clickjacking defence in depth
      * X-Frame-Options DENY — legacy clickjacking guard (CSP frame-ancestors
        is the modern equivalent but X-Frame-Options is still respected by
        old browsers)
      * X-Content-Type-Options nosniff — prevents MIME-type sniffing attacks
      * Referrer-Policy strict-origin-when-cross-origin — leaks less data
        through Referer headers
      * Permissions-Policy — disables features we never use

    The middleware is idempotent: if a downstream handler already set one of
    these headers (e.g. an embed iframe overriding frame-options), we don't
    overwrite it.
    """

    def __init__(self, app, csp: str | None = None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._csp = csp or _CSP_DIRECTIVES

    async def dispatch(  # type: ignore[override]
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        response = await call_next(request)
        h = response.headers
        h.setdefault("Content-Security-Policy", self._csp)
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(self)",
        )
        # Avoid leaking the FastAPI server signature.
        if "Server" in h:
            del h["Server"]
        return response
