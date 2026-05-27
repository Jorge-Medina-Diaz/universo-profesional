"""Course specialist — continuous learning in all its forms."""
from __future__ import annotations

from src.agents.specialists._entity_specs import COURSE_SPEC
from src.agents.specialists._helpers import build_specialist_from_spec


def build_course_specialist(*, db):  # type: ignore[no-untyped-def]
    return build_specialist_from_spec(COURSE_SPEC, db=db)
