"""AG-UI endpoints — runtime discovery + chat streams.

CopilotKit's React core auto-detects two transports:

  REST mode
    GET  /agui/info                      → runtime catalogue
    GET  /agui/threads?agentId=…         → thread list (we return 1 per user)
    POST /agui/agent/{agentId}/connect   → SSE stream
    POST /agui/agent/{agentId}/run       → SSE stream

  Single-endpoint mode
    POST /agui                           → body envelope discriminated by `method`:
                                           {"method": "info"}                          → JSON info
                                           {"method": "agent/connect", body: RunInput} → SSE
                                           {"method": "agent/run",     body: RunInput} → SSE
                                           {"method": "agent/stop"}                    → 204

We expose both so any CopilotKit version works. Discovery and status are
public; chat streams require a valid JWT (we override `forwarded_props.user_id`
and pin `thread_id = main-<user_id>` ourselves).
"""
from __future__ import annotations

from fastapi import APIRouter

# Re-export symbols accessed by tests so imports remain stable.
from src.agents.interfaces.agui_core import (  # noqa: F401
    _MAX_CONCURRENT_STREAMS_PER_USER,
    _acquire_stream_slot,
    _active_streams,
    _release_stream_slot,
)
from src.agents.interfaces.agui_transport import transport_router

router = APIRouter()

router.include_router(transport_router)
