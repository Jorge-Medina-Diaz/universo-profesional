"""Unit tests for er_rules."""
from __future__ import annotations

from src.coherence.domain.er_rules import config_for, ER_REGISTRY


class TestConfigFor:
    def test_known_kinds(self):
        for kind in ER_REGISTRY:
            assert config_for(kind) is not None

    def test_unknown_returns_none(self):
        assert config_for("nonexistent") is None
