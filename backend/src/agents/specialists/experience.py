"""Work-experience specialist — conversational discovery + structured capture."""
from __future__ import annotations

from src.agents.specialists._entity_specs import EXPERIENCE_SPEC
from src.agents.specialists._helpers import build_specialist_from_spec


def build_experience_specialist(*, db):  # type: ignore[no-untyped-def]
    return build_specialist_from_spec(EXPERIENCE_SPEC, db=db)
