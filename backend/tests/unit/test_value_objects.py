"""Unit tests for shared value objects."""
from __future__ import annotations

from datetime import date

import pytest
from src.shared.errors import ValidationError
from src.shared.value_objects import (
    DateRange,
    Email,
    Location,
    Money,
    Url,
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


class TestUrl:
    def test_parses_https(self) -> None:
        assert Url.parse("https://example.com").value == "https://example.com"

    def test_rejects_ftp(self) -> None:
        with pytest.raises(ValidationError):
            Url.parse("ftp://example.com")


class TestDateRange:
    def test_valid_range(self) -> None:
        DateRange(start=date(2020, 1, 1), end=date(2023, 1, 1))

    def test_open_ended_is_ongoing(self) -> None:
        dr = DateRange(start=date(2020, 1, 1), end=None)
        assert dr.is_ongoing

    def test_reversed_dates_raises(self) -> None:
        with pytest.raises(ValidationError):
            DateRange(start=date(2023, 1, 1), end=date(2020, 1, 1))


class TestMoney:
    def test_valid_money(self) -> None:
        Money(amount=1000, currency="EUR")

    def test_lowercase_currency_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Money(amount=1000, currency="eur")

    def test_negative_amount_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Money(amount=-100, currency="EUR")


class TestLocation:
    def test_valid_iso_country(self) -> None:
        Location(country_code="ES")

    def test_invalid_country_code(self) -> None:
        with pytest.raises(ValidationError):
            Location(country_code="ESP")


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
