"""Unit tests for ESCO linker normalisation."""
from __future__ import annotations

from src.graph.application.esco_linker import normalise


class TestNormalise:
    def test_empty(self):
        assert normalise("") == ""

    def test_lowercase(self):
        assert normalise("Python") == "python"

    def test_abbrev_expansion(self):
        assert normalise("AWS") == "amazon web services"
        assert normalise("k8s") == "kubernetes"

    def test_nfkc(self):
        assert normalise("ＡＢＣ") == "abc"
