"""Certification specialist — professional credentials with context."""
from __future__ import annotations

from src.agents.specialists._entity_specs import CERTIFICATION_SPEC
from src.agents.specialists._helpers import build_specialist_from_spec


def build_certification_specialist(*, db):  # type: ignore[no-untyped-def]
    return build_specialist_from_spec(CERTIFICATION_SPEC, db=db)
