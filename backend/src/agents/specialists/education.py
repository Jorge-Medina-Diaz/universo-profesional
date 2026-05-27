"""Education specialist — from degrees to continuous learning."""
from __future__ import annotations

from src.agents.specialists._entity_specs import EDUCATION_SPEC
from src.agents.specialists._helpers import build_specialist_from_spec


def build_education_specialist(*, db):  # type: ignore[no-untyped-def]
    return build_specialist_from_spec(EDUCATION_SPEC, db=db)
