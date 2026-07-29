"""Module-level port variables for Apache AGE primitives.

Wired by ``src.graph.infrastructure.age_client`` and
``src.graph.infrastructure.age_repository`` at import time so the
application layer can stay free of direct infrastructure imports.

The defaults are a *raising sentinel* rather than ``None``. Two reasons:
the ports are non-Optional for a type checker (a ``| None`` default made
every call site a "None not callable" error), and calling one before the
infrastructure has been imported now says so, instead of failing with
``TypeError: 'NoneType' object is not callable`` several frames away.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, NoReturn


def _unwired(*_args: Any, **_kwargs: Any) -> NoReturn:
    raise RuntimeError(
        "Apache AGE ports are not wired. Import `src.main` (or call the "
        "wiring in src.graph.infrastructure.age_client) before using them."
    )


# Rebound at runtime by the infrastructure modules.
cypher: Callable[..., Any] = _unwired
parse_agtype: Callable[[Any], Any] = _unwired
ensure_age_loaded: Callable[..., Any] = _unwired
age_graph_repository: Any = None
