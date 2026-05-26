"""Prometheus counters for business + system events."""
from __future__ import annotations

from typing import Any

from prometheus_client import Counter, Histogram

user_registered_total = Counter(
    "cvs_user_registered_total", "Total user registrations"
)
logins_total = Counter("cvs_logins_total", "Total successful logins")
cvs_generated_total = Counter(
    "cvs_documents_generated_total", "Total documents generated", ["kind"]
)
cv_generated_total = Counter(
    "cvs_cv_generated_total", "Total CVs generated (business metric)", ["kind"]
)
mcp_invocations_total = Counter(
    "cvs_mcp_invocations_total", "Total MCP tool invocations", ["tool", "ok"]
)
stripe_conversion_total = Counter(
    "cvs_stripe_conversion_total",
    "Total Stripe plan conversions",
    ["plan", "event"],
)
mcp_latency_seconds = Histogram(
    "cvs_mcp_latency_seconds",
    "MCP tool call latency in seconds",
    ["tool"],
)
errors_total = Counter("cvs_errors_total", "Total errors by code", ["code"])


# --- Agentic chat observability -------------------------------------------
# The agentic path had zero token/cost visibility. These let us track run
# volume, latency, error rate, and (where the model exposes it) token spend
# so cost drift and infinite-loop patterns are detectable before they hit a
# provider quota wall.
agent_runs_total = Counter(
    "cvs_agent_runs_total", "Agent/team chat runs", ["agent", "status"]
)
agent_run_seconds = Histogram(
    "cvs_agent_run_seconds", "Agent/team run wall-clock latency", ["agent"]
)
agent_tokens_total = Counter(
    "cvs_agent_tokens_total",
    "LLM tokens consumed by agent runs",
    ["agent", "kind"],
)

_TOKEN_KINDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "total_tokens",
)


def record_agent_tokens(agent: str, metrics_obj: Any) -> dict[str, int]:
    """Increment token counters from an Agno run `metrics` object.

    Returns a plain dict for structured logging. Safe on None / partial
    objects (e.g. the mock provider exposes no metrics) — never raises, so
    callers can use it without guarding.
    """
    out: dict[str, int] = {}
    if metrics_obj is None:
        return out
    for kind in _TOKEN_KINDS:
        try:
            val = int(getattr(metrics_obj, kind, 0) or 0)
        except (TypeError, ValueError):
            val = 0
        if val:
            agent_tokens_total.labels(agent=agent, kind=kind).inc(val)
        out[kind] = val
    return out
