"""structlog configuration — JSON in production, console-friendly in dev."""
from __future__ import annotations

import hashlib
import logging
import re
import sys

import structlog
from structlog.types import EventDict, Processor

from .config import get_settings

# Regexes for PII redaction. We hash emails (so we can still correlate
# events from the same user without leaking the address) and replace token-
# shaped strings outright.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")
_BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+")
_API_KEY_RE = re.compile(r"sk_(live|test)_[A-Za-z0-9]+")
_PII_KEYS = {
    "email",
    "to",
    "from",
    "user_email",
    "recipient",
    "password",
    "token",
    "refresh_token",
    "access_token",
    "api_key",
    "secret",
    "authorization",
}


def _hash_email(value: str) -> str:
    """Replace each email with a stable short hash so we can group events."""
    def _repl(match: re.Match[str]) -> str:
        digest = hashlib.sha256(match.group(0).encode("utf-8")).hexdigest()[:10]
        return f"<email:{digest}>"

    return _EMAIL_RE.sub(_repl, value)


def _scrub_value(value: object) -> object:
    if isinstance(value, str):
        s = value
        s = _hash_email(s)
        s = _JWT_RE.sub("<jwt-redacted>", s)
        s = _BEARER_RE.sub("Bearer <redacted>", s)
        s = _API_KEY_RE.sub("<stripe-key-redacted>", s)
        return s
    if isinstance(value, dict):
        return {k: _scrub_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    return value


def _redact_pii(_logger: object, _method: str, event_dict: EventDict) -> EventDict:
    """Hash emails + redact tokens in every event field.

    Applied in production only — dev logs keep raw values so you can spot
    bugs in the data flow. Test env also keeps raw values for assertions.
    """
    for key, value in list(event_dict.items()):
        if key in _PII_KEYS and isinstance(value, str):
            event_dict[key] = "[redacted]"
            continue
        event_dict[key] = _scrub_value(value)
    return event_dict


def _add_request_id(_logger: object, _method: str, event_dict: EventDict) -> EventDict:
    # Request id is set by the FastAPI middleware via contextvars
    return event_dict


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.add_log_level,
        _add_request_id,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    # PII redaction is prod-only — dev keeps raw values for debugging.
    if settings.is_prod:
        shared_processors.append(_redact_pii)

    if settings.is_dev:
        renderer: Processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Quiet noisy libs
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
