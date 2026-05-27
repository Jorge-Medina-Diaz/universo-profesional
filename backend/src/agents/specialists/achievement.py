"""Achievement specialist — surfacing impact and recognition."""
from __future__ import annotations

from src.agents.specialists._entity_specs import ACHIEVEMENT_SPEC
from src.agents.specialists._helpers import build_specialist_from_spec


def build_achievement_specialist(*, db):  # type: ignore[no-untyped-def]
    return build_specialist_from_spec(ACHIEVEMENT_SPEC, db=db)
