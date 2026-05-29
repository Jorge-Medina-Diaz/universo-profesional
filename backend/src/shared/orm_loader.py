"""ORM model loader — imports every ORM module so SQLAlchemy registers tables.

Called by Alembic env, FastAPI lifespan, and arq worker startup.
Kept separate from `shared.db` to avoid indirect Clean Architecture
violations (application layers importing `shared.db` would transitively
pull in every bounded context's infrastructure.orm).
"""
from __future__ import annotations


def import_all_models() -> None:
    """Import every ORM module so SQLAlchemy registers tables on `Base.metadata`."""

    from src.billing.infrastructure import orm as _billing  # noqa: F401
    from src.coherence.infrastructure import orm as _coherence  # noqa: F401
    from src.documents.infrastructure import orm as _documents  # noqa: F401
    from src.identity.infrastructure import orm as _identity  # noqa: F401
    from src.integrations.infrastructure import orm as _integrations  # noqa: F401
    from src.llm_tracking.infrastructure import orm as _llm_tracking  # noqa: F401
    from src.mcp_server.infrastructure import orm as _mcp  # noqa: F401
    from src.notes.infrastructure import orm as _notes  # noqa: F401
    from src.rubrics.infrastructure import orm as _rubrics  # noqa: F401
    from src.universe.infrastructure import orm as _universe  # noqa: F401
