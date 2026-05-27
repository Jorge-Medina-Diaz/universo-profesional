"""Language specialist — multilingual competence with context."""
from __future__ import annotations

from src.agents.specialists._entity_specs import LANGUAGE_SPEC
from src.agents.specialists._helpers import build_specialist_from_spec


def build_language_specialist(*, db):  # type: ignore[no-untyped-def]
    return build_specialist_from_spec(LANGUAGE_SPEC, db=db)
