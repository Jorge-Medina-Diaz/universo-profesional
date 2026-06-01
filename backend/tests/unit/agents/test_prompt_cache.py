"""R14: guard that Anthropic prompt-cache breakpoints stay enabled on the model.

Caching the (static) system prompt + tool schema cuts input-token cost ~70% on
busy chats. This pins it so a refactor can't silently drop the breakpoint.
"""
from __future__ import annotations

import pytest

from src.agents import factory

_FAKE = ("anthropic", "sk-ant-fake-key-for-construction-only")


@pytest.mark.parametrize("tier", ["coordinator", "specialist"])
def test_anthropic_model_keeps_cache_breakpoints(tier):
    token = factory._byok_override.set(_FAKE)
    try:
        model = factory._build_model(tier)
    finally:
        factory._byok_override.reset(token)
    # The cached system prefix + tool schema are the input-cost breakpoint.
    assert getattr(model, "cache_system_prompt", False) is True
    assert getattr(model, "cache_tools", False) is True
