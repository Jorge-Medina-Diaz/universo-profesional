"""Unit tests for IntentRouter."""
from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.agents.context_providers.router import IntentRouter


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def router(mock_session):
    return IntentRouter(mock_session, uuid4())


class TestClassifyFastPath:
    async def test_expand_universe_keywords(self, router):
        intent = await router.classify("Añade una nueva experiencia laboral")
        assert intent.name == "expand_universe"
        assert intent.confidence == 0.85

    async def test_generate_document_keywords(self, router):
        intent = await router.classify("Genera mi cv en pdf")
        assert intent.name == "generate_document"
        assert intent.confidence == 0.9

    async def test_explore_graph_keywords(self, router):
        intent = await router.classify("Explora mi grafo profesional")
        assert intent.name == "explore_graph"
        assert intent.confidence == 0.85

    async def test_discover_profile_keywords(self, router):
        intent = await router.classify("Descubre mi perfil completo")
        assert intent.name == "discover_profile"
        assert intent.confidence == 0.85

    async def test_quiz_skills_removed(self, router):
        """quiz_skills intent was removed per user directive — no exams."""
        intent = await router.classify("Hazme un test de habilidades")
        # Should NOT match quiz_skills (removed); falls through to default
        assert intent.name != "quiz_skills"

    async def test_short_message_is_general_chat(self, router):
        intent = await router.classify("Hola")
        assert intent.name == "general_chat"

    async def test_default_is_expand_universe(self, router):
        intent = await router.classify("Trabajé como desarrollador durante dos años en una startup")
        assert intent.name == "expand_universe"


class TestGetProvider:
    async def test_universe_curator_provider(self, router):
        from src.agents.context_providers.universe_provider import UniverseContextProvider

        intent = await router.classify("Añade experiencia")
        provider = await router.get_provider(intent)
        assert isinstance(provider, UniverseContextProvider)

    async def test_document_engineer_provider(self, router):
        from src.agents.context_providers.document_provider import DocumentContextProvider

        intent = await router.classify("Genera mi CV")
        provider = await router.get_provider(intent)
        assert isinstance(provider, DocumentContextProvider)
