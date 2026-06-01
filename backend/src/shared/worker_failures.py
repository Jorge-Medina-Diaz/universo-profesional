"""Single fail-loud policy for arq background tasks.

Several tasks swallowed terminal failures (`except Exception: return {ok: False}`),
so a broken sync was recorded as a *successful* job — invisible to the user and
to ops, which violates the no-silent-errors rule. This module classifies a task
exception and escalates it:

  * transient (network/timeout) → ``arq.Retry`` with bounded exponential backoff
    so the task is retried instead of burning all of arq's default tries instantly;
  * terminal → capture to Sentry (the worker wires no ArqIntegration, so this must
    be explicit) + structured log + re-raise so arq records the job as failed.

Lives in ``src.shared`` (not a layered container) so any infrastructure-layer
task may import it without crossing architecture layers.
"""
from __future__ import annotations

import asyncio
from typing import Any, NoReturn

import structlog
from arq import Retry

from src.shared.metrics import task_runs_total

logger = structlog.get_logger(__name__)

# Exceptions worth retrying with backoff rather than failing immediately.
TRANSIENT_EXC: tuple[type[BaseException], ...] = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)
try:  # httpx ships with the app, but stay defensive at import time
    import httpx

    TRANSIENT_EXC = TRANSIENT_EXC + (httpx.TransportError,)
except Exception:  # pragma: no cover - httpx always present in practice
    pass

_MAX_BACKOFF_SECONDS = 300


def backoff_seconds(job_try: int) -> int:
    """Exponential backoff (2, 4, 8, …) capped at five minutes."""
    return min(_MAX_BACKOFF_SECONDS, 2 ** max(1, int(job_try)))


def handle_task_exception(
    ctx: dict[str, Any], exc: Exception, *, task: str, **log_fields: Any
) -> NoReturn:
    """Classify and escalate *exc*. Never returns.

    Transient → ``raise arq.Retry(defer=backoff)``. Terminal → capture to
    Sentry, log, and re-raise so the job is marked failed (fail loud).
    """
    job_try = int(ctx.get("job_try", 1) or 1)
    if isinstance(exc, TRANSIENT_EXC):
        task_runs_total.labels(task=task, status="retry").inc()
        logger.warning(
            "task_transient_failure",
            task=task,
            job_try=job_try,
            error=str(exc),
            **log_fields,
        )
        raise Retry(defer=backoff_seconds(job_try))

    task_runs_total.labels(task=task, status="failed").inc()
    try:
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
    except Exception:  # pragma: no cover - Sentry is optional
        pass
    logger.exception("task_failed", task=task, error=str(exc), **log_fields)
    raise exc
