"""Shared value objects reused across contexts."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Self

from .errors import ValidationError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
