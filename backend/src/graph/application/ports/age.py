"""Module-level port variables for Apache AGE primitives.

Wired by ``src.graph.infrastructure.age_client`` and
``src.graph.infrastructure.age_repository`` at import time so the
application layer can stay free of direct infrastructure imports.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

# These are wired at runtime by the infrastructure modules.
cypher: Callable[..., Any] | None = None
parse_agtype: Callable[[Any], Any] | None = None
ensure_age_loaded: Callable[..., Any] | None = None
age_graph_repository: Any | None = None
