"""Unit tests for UniverseGraphService with a mock repository (no DB)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.graph.application.universe_graph import UniverseGraphService
from src.graph.domain import schema


class _MockGraphRepo:
    async def execute(self, session, graph, query, params=None, column_defs="result agtype"):
        return []

    def parse_result(self, value):
        return value

    async def ensure_loaded(self, session):
        pass


class TestUpsertEdgeValidation:
    async def test_invalid_edge_type_lowercase(self):
        svc = UniverseGraphService(_MockGraphRepo())
        with pytest.raises(ValueError, match="UPPER_SNAKE"):
            await svc.upsert_edge(
                MagicMock(), edge_type="uses_tech", source_id=uuid4(), target_id=uuid4(), user_id=uuid4()
            )

    async def test_invalid_edge_type_non_identifier(self):
        svc = UniverseGraphService(_MockGraphRepo())
        with pytest.raises(ValueError, match="UPPER_SNAKE"):
            await svc.upsert_edge(
                MagicMock(), edge_type="USES-TECH", source_id=uuid4(), target_id=uuid4(), user_id=uuid4()
            )

    async def test_valid_edge_type(self):
        repo = _MockGraphRepo()
        repo.execute = AsyncMock(return_value=[{"r": "dummy"}])
        svc = UniverseGraphService(repo)
        result = await svc.upsert_edge(
            MagicMock(), edge_type="USES_TECH", source_id=uuid4(), target_id=uuid4(), user_id=uuid4()
        )
        assert result is True


class TestExpireEdgeValidation:
    async def test_invalid_edge_type(self):
        svc = UniverseGraphService(_MockGraphRepo())
        with pytest.raises(ValueError):
            await svc.expire_edge(
                MagicMock(), edge_type="invalid", source_id=uuid4(), target_id=uuid4(), user_id=uuid4()
            )


class TestInvalidateContradictingEdgesValidation:
    async def test_invalid_edge_type(self):
        svc = UniverseGraphService(_MockGraphRepo())
        with pytest.raises(ValueError):
            await svc.invalidate_contradicting_edges(
                MagicMock(), edge_type="invalid", source_id=uuid4(), user_id=uuid4(), keep_target_id=uuid4()
            )


class TestNeighborsValidation:
    async def test_depth_too_low(self):
        svc = UniverseGraphService(_MockGraphRepo())
        with pytest.raises(ValueError, match="depth must be in"):
            await svc.neighbors(MagicMock(), entity_id=uuid4(), user_id=uuid4(), depth=0)

    async def test_depth_too_high(self):
        svc = UniverseGraphService(_MockGraphRepo())
        with pytest.raises(ValueError, match="depth must be in"):
            await svc.neighbors(MagicMock(), entity_id=uuid4(), user_id=uuid4(), depth=5)

    async def test_limit_clamped(self):
        repo = _MockGraphRepo()
        repo.execute = AsyncMock(return_value=[])
        svc = UniverseGraphService(repo)
        await svc.neighbors(MagicMock(), entity_id=uuid4(), user_id=uuid4(), limit=5000)
        # Query should contain LIMIT 2000
        call = repo.execute.call_args
        assert "LIMIT 2000" in call.args[2]

    async def test_edge_kinds_filtered(self):
        repo = _MockGraphRepo()
        repo.execute = AsyncMock(return_value=[])
        svc = UniverseGraphService(repo)
        await svc.neighbors(
            MagicMock(), entity_id=uuid4(), user_id=uuid4(), edge_kinds=["USES_TECH", "invalid-one"]
        )
        call = repo.execute.call_args
        # Only valid UPPER_SNAKE kinds should appear
        assert "USES_TECH" in call.args[2]
        assert "invalid-one" not in call.args[2]
