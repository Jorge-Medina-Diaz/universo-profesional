"""Prometheus counters for business + system events."""
from __future__ import annotations

from prometheus_client import Counter, Histogram

registrations_total = Counter(
    "cvs_registrations_total", "Total user registrations"
)
logins_total = Counter("cvs_logins_total", "Total successful logins")
cvs_generated_total = Counter(
    "cvs_documents_generated_total", "Total documents generated", ["kind"]
)
mcp_invocations_total = Counter(
    "cvs_mcp_invocations_total", "Total MCP tool invocations", ["tool", "ok"]
)
mcp_latency_seconds = Histogram(
    "cvs_mcp_latency_seconds",
    "MCP tool call latency in seconds",
    ["tool"],
)
errors_total = Counter("cvs_errors_total", "Total errors by code", ["code"])
