"""Sentry initialization — no-op if SENTRY_DSN is not configured.

We avoid forcing every dev to install/configure Sentry. When the DSN is
set, `sentry_sdk.init` wires the FastAPI / SQLAlchemy / asyncio / structlog
integrations and we get error reporting + lightweight traces for free.

PII safety: `send_default_pii=False` and we attach a `before_send` filter
that strips Authorization headers + obvious token-shaped strings from the
event payload before it leaves the host.
"""
from __future__ import annotations

import re
from typing import Any

from src.shared.config import get_settings

_TOKEN_RE = re.compile(r"(eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)|(sk_[A-Za-z0-9]+)")


def _scrub_pii(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    request = event.get("request", {})
    if request:
        headers = request.get("headers") or {}
        for h in list(headers.keys()):
            if h.lower() in {"authorization", "cookie", "x-api-key"}:
                headers[h] = "[redacted]"
        request["headers"] = headers
    # Strip tokens from any string anywhere in the event tree.
    def _walk(node: Any) -> Any:
        if isinstance(node, dict):
            return {k: _walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_walk(x) for x in node]
        if isinstance(node, str):
            return _TOKEN_RE.sub("[redacted-token]", node)
        return node

    return _walk(event)


def init_sentry() -> None:
    """Initialize Sentry if SENTRY_DSN is configured. Safe no-op otherwise."""
    settings = get_settings()
    if not settings.sentry_dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.env,
        # 10% trace sampling — enough to spot trends without exploding cost.
        traces_sample_rate=0.1 if settings.is_prod else 1.0,
        send_default_pii=False,
        before_send=_scrub_pii,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            AsyncioIntegration(),
        ],
    )
