"""Project specialist — from vague ideas to structured portfolio entries."""
from __future__ import annotations

from src.agents.specialists._entity_specs import PROJECT_SPEC
from src.agents.specialists._helpers import build_specialist_from_spec


def build_project_specialist(*, db):  # type: ignore[no-untyped-def]
    return build_specialist_from_spec(PROJECT_SPEC, db=db)
