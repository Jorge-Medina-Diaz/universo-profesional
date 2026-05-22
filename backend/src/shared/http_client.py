"""Shared httpx client factory with retries + timeout + request logging.

Every outbound HTTP call (GitHub, LinkedIn, BrightData, Stripe, Brevo, …)
should go through this factory so we get consistent behaviour:

  * Timeout: 15s connect, 30s read by default — overridable per-call.
  * Retries: up to 3 attempts with exponential backoff on transient
    failures (network errors + 502/503/504 responses). 4xx is NOT
    retried; the caller deals with it.
  * Logging: every request emits a structured log line with method, URL,
    status, latency. Sensitive headers (Authorization, api-key) are
    redacted before logging.
  * Sentry breadcrumbs: optional — added automatically if Sentry is init.

Usage:

    async with make_http_client() as client:
        resp = await client.get("https://api.example.com/v1/x")

Or for the long-lived clients (Stripe, Brevo) you keep one per instance
and let it close on shutdown.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


_REDACT_HEADERS = {"authorization", "api-key", "x-api-key", "cookie", "stripe-signature"}


class _RetryableHttpError(Exception):
    """Wrapper raised for HTTP 5xx responses so tenacity can retry them."""


def _is_retryable(exc: BaseException) -> bool:
    """Return True when an exception should trigger a retry."""
    if isinstance(exc, (_RetryableHttpError, httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {502, 503, 504}
    return False


async def _log_request(request: httpx.Request) -> None:
    safe_headers = {
        k: ("[redacted]" if k.lower() in _REDACT_HEADERS else v)
        for k, v in request.headers.items()
    }
    logger.debug(
        "http_outbound_request",
        method=request.method,
        url=str(request.url),
        headers=safe_headers,
    )


async def _log_response(response: httpx.Response) -> None:
    logger.info(
        "http_outbound_response",
        method=response.request.method,
        url=str(response.request.url),
        status=response.status_code,
        elapsed_ms=int(response.elapsed.total_seconds() * 1000),
    )
    if response.status_code >= 500:
        # Mark as retryable so tenacity (when applied) picks it up.
        raise _RetryableHttpError(
            f"upstream 5xx: {response.request.method} {response.request.url} -> {response.status_code}"
        )


def make_http_client(
    *,
    timeout: float = 30.0,
    connect_timeout: float = 15.0,
    base_url: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> httpx.AsyncClient:
    """Build an `AsyncClient` with the standard hooks pre-wired.

    Caller is responsible for closing the client (use `async with`). For
    automatic retries on a specific call, wrap it with `retry_call(...)`
    below.
    """
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout, connect=connect_timeout),
        base_url=base_url or "",
        headers=dict(headers or {}),
        event_hooks={"request": [_log_request], "response": [_log_response]},
    )


async def retry_call(coro_factory: Any, *, attempts: int = 3) -> Any:
    """Run `coro_factory()` with tenacity retry on transient errors.

    `coro_factory` must be a zero-arg callable returning a fresh coroutine
    each time (so retries get a new HTTP request, not the consumed one).
    """
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(
            (_RetryableHttpError, httpx.TimeoutException, httpx.NetworkError)
        ),
        reraise=True,
    ):
        with attempt:
            return await coro_factory()
    return None  # unreachable — tenacity raises on failure
