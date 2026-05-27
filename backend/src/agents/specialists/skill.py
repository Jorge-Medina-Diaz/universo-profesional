"""Skill specialist — conversational discovery + level calibration."""
from __future__ import annotations

from src.agents.specialists._entity_specs import SKILL_SPEC
from src.agents.specialists._helpers import build_specialist_from_spec


def build_skill_specialist(*, db):  # type: ignore[no-untyped-def]
    return build_specialist_from_spec(SKILL_SPEC, db=db)
