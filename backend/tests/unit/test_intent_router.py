"""Tests for Intent Router (pure keyword matching, no DB required)."""
from __future__ import annotations

from uuid import UUID

import pytest

from src.agents.context_providers.router import IntentRouter


class TestIntentRouterFastPath:
    """Keyword-based classification — zero LLM cost."""

    @pytest.fixture
    def router(self, mocker):
        session = mocker.AsyncMock()
        return IntentRouter(session, UUID("11111111-1111-1111-1111-111111111111"))

    @pytest.mark.asyncio
    async def test_cv_intent(self, router) -> None:
        intent = await router.classify("Genera mi CV en formato funcional")
        assert intent.name == "generate_document"
        assert intent.provider_name == "document_engineer"
        assert intent.confidence >= 0.8

    @pytest.mark.asyncio
    async def test_explore_graph_intent(self, router) -> None:
        intent = await router.classify("muéstrame mi trayectoria profesional")
        assert intent.name == "explore_graph"
        assert intent.provider_name == "universe_curator"

    @pytest.mark.asyncio
    async def test_discover_profile_intent(self, router) -> None:
        intent = await router.classify("qué me falta en mi perfil")
        assert intent.name == "discover_profile"
        assert intent.provider_name == "universe_curator"

    @pytest.mark.asyncio
    async def test_expand_universe_agrega_intent(self, router) -> None:
        intent = await router.classify("agrega una nueva habilidad")
        assert intent.name == "expand_universe"
        assert intent.provider_name == "universe_curator"

    @pytest.mark.asyncio
    async def test_expand_universe_intent(self, router) -> None:
        intent = await router.classify("Añade una nueva experiencia en Google")
        assert intent.name == "expand_universe"
        assert intent.provider_name == "universe_curator"

    @pytest.mark.asyncio
    async def test_short_message_defaults_to_chat(self, router) -> None:
        intent = await router.classify("hola")
        assert intent.name == "general_chat"

    @pytest.mark.asyncio
    async def test_ambiguous_defaults_to_universe(self, router) -> None:
        intent = await router.classify("algo random que no encaja")
        assert intent.name == "expand_universe"
        assert intent.provider_name == "universe_curator"


class TestIntentRouterProviderMapping:
    """Ensure every intent maps to a real provider class."""

    @pytest.fixture
    def router(self, mocker):
        session = mocker.AsyncMock()
        return IntentRouter(session, UUID("11111111-1111-1111-1111-111111111111"))

    @pytest.mark.asyncio
    async def test_all_intents_resolve_to_provider(self, router) -> None:
        from src.agents.context_providers import BaseContextProvider

        test_messages = [
            "Genera mi CV",
            "Busco trabajo",
            "Hazme un quiz",
            "Quiero conectar",
            "Añade experiencia",
        ]
        for msg in test_messages:
            intent = await router.classify(msg)
            provider = await router.get_provider(intent)
            assert isinstance(provider, BaseContextProvider)
