"""Context Providers — scoped knowledge + memory for agent domains.

Usage:
    from src.agents.context_providers import IntentRouter
    router = IntentRouter(session, user_id)
    intent = await router.classify(user_message)
    provider = await router.get_provider(intent)
    memory_ctx = await provider.get_memory_context()
"""
from __future__ import annotations

from src.agents.context_providers.base import BaseContextProvider
from src.agents.context_providers.document_provider import DocumentContextProvider
from src.agents.context_providers.router import IntentRouter
from src.agents.context_providers.universe_provider import UniverseContextProvider

__all__ = [
    "BaseContextProvider",
    "DocumentContextProvider",
    "IntentRouter",
    "UniverseContextProvider",
]
