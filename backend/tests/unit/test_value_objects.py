"""Unit tests for shared value objects."""
from __future__ import annotations

import pytest
from src.shared.errors import ValidationError
from src.shared.value_objects import (
    Email,
    validate_cefr,
    validate_skill_level,
)


class TestEmail:
    def test_parses_valid_email(self) -> None:
        assert Email.parse("Jorge@WebTools.es").value == "jorge@webtools.es"

    def test_rejects_missing_at(self) -> None:
        with pytest.raises(ValidationError):
            Email.parse("not-an-email")

    def test_rejects_too_long(self) -> None:
        with pytest.raises(ValidationError):
            Email.parse("a" * 250 + "@x.com")


class TestEnums:
    def test_valid_skill_level(self) -> None:
        assert validate_skill_level("expert") == "expert"

    def test_invalid_skill_level(self) -> None:
        with pytest.raises(ValidationError):
            validate_skill_level("ninja")

    def test_valid_cefr(self) -> None:
        assert validate_cefr("C1") == "C1"

    def test_native(self) -> None:
        assert validate_cefr("native") == "native"
