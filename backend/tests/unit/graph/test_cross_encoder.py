"""Unit tests for cross_encoder pure helpers (no DB)."""
from __future__ import annotations

from unittest.mock import patch

from src.graph.application.cross_encoder import _jaro_winkler


class TestJaroWinkler:
    def test_similarity(self):
        score = _jaro_winkler("python", "python")
        assert score == 1.0

    def test_fallback_on_exception(self):
        with patch("jellyfish.jaro_winkler_similarity", side_effect=ImportError):
            score = _jaro_winkler("a", "b")
            assert score == 0.0
