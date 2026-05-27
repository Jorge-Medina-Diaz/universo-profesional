"""SocialContextProvider — Networking, peer connections, community.

Knowledge namespace: "people"
Memory scope: "social_interaction"

This is intentionally a stub for the post-MVP phase.  It defines the
interface so that when we add multi-user features (connect with peers,
find mentors, team matching), the architecture is already in place.

Tools: None yet (returns empty list).  The router knows to decline
social intents gracefully until the backend is ready.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.agents.context_providers.base import BaseContextProvider


class SocialContextProvider(BaseContextProvider):
    name = "social_connector"
    knowledge_namespace = "people"
    memory_scope = "social_interaction"

    def get_tools(self) -> list[Callable[..., Any]]:
        # Stub: no tools until multi-user networking is implemented.
        return []
