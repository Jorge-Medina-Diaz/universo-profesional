"""Knowledge-document lane (P3.D) — the 5th hybrid-retrieval lane.

The knowledge store (uploaded PDFs/papers/long docs, chunked + embedded) was
previously DISCONNECTED from `hybrid_retrieve`: a question answered by a
document the user uploaded never surfaced. This lane folds chunk hits into
the same RRF fusion as the entity lanes; chunks are pseudo-entities (uuid5
of document:chunk) with the chunk text as rationale, so the agent can cite
the document by title.
"""
from __future__ import annotations

from collections.abc import Iterable
from uuid import NAMESPACE_URL, UUID, uuid5

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.application.retrieval._base import ScoredItem
from src.graph.application.retrieval._helpers import _attach_ranks

logger = structlog.get_logger(__name__)


class KnowledgeRetriever:
    name = "knowledge"

    async def retrieve(
        self,
        session: AsyncSession,
        user_id: UUID,
        query: str,
        *,
        top_k: int = 12,
        kinds: Iterable[str] | None = None,
    ) -> list[ScoredItem]:
        try:
            from src.knowledge.application.use_cases import search_knowledge

            hits = await search_knowledge(
                session, user_id=user_id, query=query, top_k=top_k
            )
        except Exception as exc:  # a dark lane degrades, never breaks fusion
            logger.warning("knowledge_retriever_failed", error=str(exc))
            return []

        items: list[ScoredItem] = []
        for h in hits:
            pseudo_id = uuid5(
                NAMESPACE_URL, f"knowledge:{h['document_id']}:{h['chunk_index']}"
            )
            excerpt = str(h.get("content") or "")[:280]
            items.append(
                ScoredItem(
                    entity_id=pseudo_id,
                    kind="knowledge_doc",
                    name=str(h.get("title") or "documento"),
                    score=float(h.get("score") or 0.0),
                    lane=self.name,
                    rationale=excerpt,
                )
            )
        return _attach_ranks(items, lane=self.name)
