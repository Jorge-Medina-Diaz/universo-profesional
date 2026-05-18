"""Shared value objects reused across contexts."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Self

from .errors import ValidationError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    @classmethod
    def parse(cls, raw: str) -> Self:
        normalized = raw.strip().lower()
        if not EMAIL_RE.match(normalized) or len(normalized) > 254:
            raise ValidationError("Invalid email address", details={"value": raw})
        return cls(normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Url:
    value: str

    @classmethod
    def parse(cls, raw: str) -> Self:
        if not URL_RE.match(raw.strip()):
            raise ValidationError("Invalid URL (must be http or https)", details={"value": raw})
        return cls(raw.strip())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class DateRange:
    start: date
    end: date | None  # None == ongoing

    def __post_init__(self) -> None:
        if self.end is not None and self.end < self.start:
            raise ValidationError(
                "DateRange.end must be >= start",
                details={"start": self.start.isoformat(), "end": self.end.isoformat()},
            )

    @property
    def is_ongoing(self) -> bool:
        return self.end is None


@dataclass(frozen=True, slots=True)
class Money:
    amount: int  # cents to avoid float drift
    currency: str

    def __post_init__(self) -> None:
        if not CURRENCY_RE.match(self.currency):
            raise ValidationError(
                "Currency must be ISO 4217 (3 uppercase letters)",
                details={"currency": self.currency},
            )
        if self.amount < 0:
            raise ValidationError("Amount cannot be negative", details={"amount": self.amount})


@dataclass(frozen=True, slots=True)
class Location:
    city: str | None = None
    region: str | None = None
    country_code: str | None = None  # ISO 3166-1 alpha-2

    def __post_init__(self) -> None:
        if self.country_code is not None and (
            len(self.country_code) != 2 or not self.country_code.isalpha()
        ):
            raise ValidationError(
                "country_code must be ISO 3166-1 alpha-2",
                details={"country_code": self.country_code},
            )


SKILL_LEVELS = ("basic", "intermediate", "high", "expert")
SkillLevel = str  # validated via SKILL_LEVELS at boundaries


def validate_skill_level(value: str) -> str:
    if value not in SKILL_LEVELS:
        raise ValidationError(
            f"Invalid skill level. Allowed: {SKILL_LEVELS}",
            details={"value": value},
        )
    return value


CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2", "native")


def validate_cefr(value: str) -> str:
    if value not in CEFR_LEVELS:
        raise ValidationError(
            f"Invalid CEFR level. Allowed: {CEFR_LEVELS}",
            details={"value": value},
        )
    return value
