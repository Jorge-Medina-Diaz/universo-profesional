"""Unit tests for agents tools _deps (pure, no DB)."""
from __future__ import annotations

from types import SimpleNamespace

from src.agents.tools._deps import require_user_id


class TestRequireUserId:
    async def test_missing_user_id(self):
        @require_user_id
        async def tool_fn(run_context, query: str):
            return {"ok": True}

        ctx = SimpleNamespace(user_id="")
        result = await tool_fn(ctx, "q")
        assert result["ok"] is False
        assert "missing user_id" in result["error"]

    async def test_present_user_id(self):
        @require_user_id
        async def tool_fn(run_context, query: str):
            return {"ok": True, "query": query}

        ctx = SimpleNamespace(user_id="u1")
        result = await tool_fn(ctx, "q")
        assert result["ok"] is True

    async def test_entrypoint_missing_user_id(self):
        @require_user_id
        async def tool_fn(run_context, query: str):
            return {"ok": True}

        # Simulate Agno @tool entrypoint wrapper
        tool_fn.entrypoint = tool_fn
        ctx = SimpleNamespace(user_id="")
        result = await tool_fn.entrypoint(ctx, "q")
        assert result["ok"] is False
