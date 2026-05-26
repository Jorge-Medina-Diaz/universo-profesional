"""Knowledge-base tools — memory layer 4 (long documents: PDFs, papers).

Backed by the native knowledge store (pgvector + RLS). The graph hybrid
retriever covers structured entities; this covers long unstructured
documents the user has uploaded or imported.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from agno.run.base import RunContext
from agno.tools import tool

from src.knowledge.application.use_cases import search_knowledge as _search
from src.shared.db import with_user_session

logger = structlog.get_logger(__name__)


@tool(
    name="search_knowledge",
    description=(
        "Semantic search over the user's uploaded documents and papers "
        "(memory layer 4: long unstructured content, not structured "
        "universe entities). Returns the most relevant passages with their "
        "source document title. Use to ground answers about topics the user "
        "has accumulated reading on — e.g. 'what did that paper on RAG say "
        "about reranking?'. For skills/projects/experiences use "
        "universe_retrieve instead."
    ),
)
async def search_knowledge(
    run_context: RunContext,
    query: str,
    top_k: int = 5,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id", "results": []}
    async with with_user_session(UUID(str(user_id))) as session:
        results = await _search(
            session,
            user_id=UUID(str(user_id)),
            query=query,
            top_k=top_k,
            tags=tags,
        )
    return {"ok": True, "results": results}
