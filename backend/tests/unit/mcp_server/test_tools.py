"""Unit tests for MCP tool handlers (pure / mocked, no DB)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.mcp_server.tools import (
    TOOL_DEFINITIONS,
    TOOL_HANDLERS,
    _TOOL_SCOPES,
    _create_entity,
    _delete_entity,
    _read_entity,
    _repo_for,
    _update_entity,
)
from src.universe.application.registry import CrudRegistry


class TestToolDefinitions:
    def test_has_expected_tools(self):
        names = {t.name for t in TOOL_DEFINITIONS}
        assert "read_universe_summary" in names
        assert "create_entity" in names
        assert "generate_cv" in names


class TestToolScopes:
    def test_read_scope(self):
        assert _TOOL_SCOPES["read_universe_summary"] == "universe:read"

    def test_write_scope(self):
        assert _TOOL_SCOPES["create_entity"] == "universe:write"

    def test_all_tools_have_handler(self):
        for tool in TOOL_DEFINITIONS:
            assert tool.name in TOOL_HANDLERS


class TestRepoFor:
    def test_skill(self):
        class FakeRepo:
            def __init__(self, session):
                self.session = session

        with patch.object(CrudRegistry, "get_repo_class", return_value=FakeRepo):
            session = MagicMock()
            repo = _repo_for("skill", session)
            assert repo is not None
            assert repo.session is session


class TestCreateEntity:
    async def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown entity type"):
            await _create_entity(user_id=uuid4(), args={"entity_type": "unicorn", "data": {}})

    async def test_success(self):
        with patch("src.mcp_server.tools.set_proposal") as mock_set:
            result = await _create_entity(
                user_id=uuid4(), args={"entity_type": "skill", "data": {"name": "Python"}}
            )
            assert result["action"] == "create"
            assert result["proposal_id"]
            mock_set.assert_called_once()


class TestUpdateEntity:
    async def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown entity type"):
            await _update_entity(
                user_id=uuid4(), args={"entity_type": "unicorn", "entity_id": str(uuid4()), "data": {}}
            )

    async def test_success(self):
        with patch("src.mcp_server.tools.set_proposal") as mock_set:
            result = await _update_entity(
                user_id=uuid4(),
                args={"entity_type": "skill", "entity_id": str(uuid4()), "data": {"level": "expert"}},
            )
            assert result["action"] == "update"
            mock_set.assert_called_once()


class TestDeleteEntity:
    async def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown entity type"):
            await _delete_entity(
                user_id=uuid4(), args={"entity_type": "unicorn", "entity_id": str(uuid4())}
            )

    async def test_success(self):
        with patch("src.mcp_server.tools.set_proposal") as mock_set:
            result = await _delete_entity(
                user_id=uuid4(), args={"entity_type": "skill", "entity_id": str(uuid4())}
            )
            assert result["action"] == "delete"
            mock_set.assert_called_once()


class TestReadEntity:
    async def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown entity type"):
            await _read_entity(user_id=uuid4(), args={"entity_type": "unicorn"})

    async def test_neither_id_nor_name_raises(self):
        with pytest.raises(ValueError, match="Provide either"):
            with patch("src.mcp_server.tools._repo_for") as mock_repo:
                mock_repo.return_value = MagicMock()
                await _read_entity(user_id=uuid4(), args={"entity_type": "skill"})
