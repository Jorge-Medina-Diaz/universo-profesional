"""Unit tests for domain_templates."""
from __future__ import annotations

from src.agents.domain_templates import _canonical, fallback_template, get_template_for


class TestCanonical:
    def test_exact_match(self):
        assert _canonical("ecommerce") == "ecommerce"

    def test_alias(self):
        assert _canonical("ai") == "ai_ml"
        assert _canonical("E-COMMERCE") == "ecommerce"

    def test_unknown(self):
        assert _canonical("magic") == "magic"


class TestGetTemplateFor:
    def test_known(self):
        assert get_template_for("ecommerce") is not None

    def test_alias(self):
        assert get_template_for("ai") is not None

    def test_unknown(self):
        assert get_template_for("magic") is None


class TestFallbackTemplate:
    def test_has_sections(self):
        t = fallback_template("magic")
        assert "sections" in t
        assert t["title"] == "Cuéntame de magic"
        assert len(t["sections"]) == 5
        ids = [s["id"] for s in t["sections"]]
        assert ids == ["stack", "modules", "depth", "sources", "notes"]
