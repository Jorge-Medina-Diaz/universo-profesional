"""Unit tests: identity password policy enforcement."""
from __future__ import annotations

import pytest
from src.identity.interfaces.api.schemas import _validate_password


class TestPasswordPolicy:
    def test_too_short_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least"):
            _validate_password("Short1!")

    def test_missing_digit_rejected(self) -> None:
        with pytest.raises(ValueError, match="digit"):
            _validate_password("NoDigitsHere!")

    def test_missing_uppercase_rejected(self) -> None:
        with pytest.raises(ValueError, match="uppercase"):
            _validate_password("alllower1234")

    def test_common_password_rejected(self) -> None:
        with pytest.raises(ValueError, match="common"):
            _validate_password("Password1234")

    def test_valid_password_accepted(self) -> None:
        assert _validate_password("S3cur3-Passw0rd!") == "S3cur3-Passw0rd!"

    def test_max_length_rejected(self) -> None:
        with pytest.raises(ValueError, match="at most"):
            _validate_password("A1" + "x" * 300)


class TestRegisterUserPasswordValidation:
    def test_schema_rejects_weak_password(self) -> None:
        from src.identity.interfaces.api.schemas import RegisterRequest

        with pytest.raises(ValueError):
            RegisterRequest(email="test@x.com", password="weak")  # noqa: S106

    def test_schema_accepts_strong_password(self) -> None:
        from src.identity.interfaces.api.schemas import RegisterRequest

        req = RegisterRequest(email="test@x.com", password="S3cur3-Passw0rd!")  # noqa: S106
        assert req.password == "S3cur3-Passw0rd!"
