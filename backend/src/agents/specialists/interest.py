"""Interest specialist — professional passions that shape trajectory."""
from __future__ import annotations

from src.agents.specialists._entity_specs import INTEREST_SPEC
from src.agents.specialists._helpers import build_specialist_from_spec


def build_interest_specialist(*, db):  # type: ignore[no-untyped-def]
    return build_specialist_from_spec(INTEREST_SPEC, db=db)
