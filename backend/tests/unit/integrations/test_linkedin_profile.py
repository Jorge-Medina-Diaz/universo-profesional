"""Unit tests for LinkedInProfile domain DTOs (pure, no DB)."""
from __future__ import annotations

from src.integrations.domain.linkedin_profile import (
    LinkedInBasics,
    LinkedInExperience,
    LinkedInProfile,
    LinkedInSkill,
)


class TestLinkedInProfile:
    def test_to_dict_empty(self):
        p = LinkedInProfile()
        d = p.to_dict()
        assert d["source"] == "linkedin"
        assert d["experiences"] == []

    def test_to_dict_nested(self):
        p = LinkedInProfile(
            basics=LinkedInBasics(name="Alice", headline="Dev"),
            experiences=[
                LinkedInExperience(organization="G", role="Dev", description="build")
            ],
            skills=[LinkedInSkill(name="Python")],
        )
        d = p.to_dict()
        assert d["basics"]["name"] == "Alice"
        assert d["experiences"][0]["organization"] == "G"
        assert d["skills"][0]["name"] == "Python"
