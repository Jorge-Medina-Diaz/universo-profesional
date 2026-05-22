"""Server-side read tools — what the coordinator and specialists can inspect.

Reads use the same RLS-scoped session pattern as writes. They never mutate
state, so no UoW is needed.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from agno.run.base import RunContext
from agno.tools import tool

from src.shared.db import get_session_factory, set_rls_user


@tool(
    name="get_universe_summary",
    description=(
        "Return a compact summary of the user's universe: counts per entity, "
        "headline, top skills, recent experiences, languages, integration status. "
        "Use to orient yourself before asking what's missing."
    ),
)
async def get_universe_summary(run_context: RunContext) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"error": "missing user_id"}
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, UUID(user_id))
        from src.universe.application.use_cases import GetUniverseSummary
        from src.universe.infrastructure.repositories import (
            SqlAlchemyCareerPreferencesRepository,
            SqlAlchemyEducationRepository,
            SqlAlchemyExperienceRepository,
            SqlAlchemyLanguageRepository,
            SqlAlchemyProjectRepository,
            SqlAlchemySkillRepository,
            SqlAlchemyUniverseRepository,
        )

        uc = GetUniverseSummary(
            SqlAlchemyUniverseRepository(session),
            SqlAlchemyEducationRepository(session),
            SqlAlchemyExperienceRepository(session),
            SqlAlchemySkillRepository(session),
            SqlAlchemyLanguageRepository(session),
            SqlAlchemyProjectRepository(session),
            SqlAlchemyCareerPreferencesRepository(session),
        )
        return await uc.execute(user_id=user_id)


@tool(
    name="find_gaps",
    description=(
        "Detect which universe entities are empty or stale so you know what to "
        "ask about next. Returns a list of suggested topics with reasons."
    ),
)
async def find_gaps(run_context: RunContext) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"error": "missing user_id"}
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, UUID(user_id))
        # Reuse the rule-based suggestions engine — it already computes the
        # "what's missing / stale" signal we need.
        from src.universe.application.suggestions import GenerateSuggestions
        from src.universe.infrastructure.repositories import (
            SqlAlchemyCareerPreferencesRepository,
            SqlAlchemyCertificationRepository,
            SqlAlchemyEducationRepository,
            SqlAlchemyExperienceRepository,
            SqlAlchemyLanguageRepository,
            SqlAlchemyProjectRepository,
            SqlAlchemySkillRepository,
        )

        uc = GenerateSuggestions(
            session=session,
            edu=SqlAlchemyEducationRepository(session),
            exp=SqlAlchemyExperienceRepository(session),
            proj=SqlAlchemyProjectRepository(session),
            skill=SqlAlchemySkillRepository(session),
            cert=SqlAlchemyCertificationRepository(session),
            lang=SqlAlchemyLanguageRepository(session),
            prefs=SqlAlchemyCareerPreferencesRepository(session),
        )
        try:
            generated = await uc.execute(user_id=user_id)
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}
        return {
            "count": len(generated or []),
            "suggestions": [
                {
                    "kind": s.get("kind"),
                    "title": s.get("title"),
                    "payload": s.get("payload"),
                }
                for s in (generated or [])
            ],
        }


@tool(
    name="search_universe",
    description=(
        "Semantic search across the user's universe. Useful to answer "
        "'did I already mention X?' before proposing a duplicate."
    ),
)
async def search_universe(
    run_context: RunContext,
    query: str,
    top_k: int = 5,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"error": "missing user_id"}
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, UUID(user_id))
        from src.shared.embeddings import get_embeddings_service
        from src.universe.application.use_cases import SearchUniverse
        from src.universe.infrastructure.semantic_search import PgVectorSemanticSearch

        uc = SearchUniverse(PgVectorSemanticSearch(session), get_embeddings_service())
        hits = await uc.execute(user_id=user_id, query=query, top_k=top_k)
        return {"hits": hits}
