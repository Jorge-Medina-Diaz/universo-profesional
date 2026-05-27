"""Certification entity."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID, uuid4

from src.universe.domain.entities import _Base


@dataclass
class Certification(_Base):
    name: str = ""
    issuer: str | None = None
    issued_on: date | None = None
    expires_on: date | None = None
    credential_id: str | None = None
    verification_url: str | None = None

    @classmethod
    def create(cls, *, user_id: UUID, name: str, **kw: Any) -> Certification:
        from src.shared.errors import ValidationError

        if not name.strip():
            raise ValidationError("Certification name is required")
        return cls(id=uuid4(), user_id=user_id, name=name.strip(), **kw)

    def embedding_text(self) -> str:
        return " — ".join(p for p in [self.name, self.issuer or ""] if p)
