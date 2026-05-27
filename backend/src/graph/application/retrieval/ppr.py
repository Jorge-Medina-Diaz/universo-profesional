from __future__ import annotations

import math
from collections.abc import Iterable
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.application.retrieval._base import ScoredItem
from src.graph.application.retrieval._helpers import _attach_ranks
from src.graph.application.retrieval.snapshot import _load_snapshot

logger = structlog.get_logger(__name__)


class PPRRetriever:
    name = "ppr"

    async def retrieve(
        self,
        session: AsyncSession,
        user_id: UUID,
        query: str,
        *,
        top_k: int = 30,
        kinds: Iterable[str] | None = None,
        seeds: list[UUID] | None = None,
    ) -> list[ScoredItem]:
        snapshot = await _load_snapshot(session, user_id)
        if snapshot.graph.vcount() == 0:
            return []
        # Seeds: either explicit (cross-lane coupling) or computed via
        # dense top-3 over the user's own entities. For Sprint O.4 the
        # orchestrator passes explicit seeds; for direct PPR queries we
        # fall back to dense.
        if seeds is None:
            seeds = await _pick_seeds_via_dense(session, user_id, query)
        if not seeds:
            return []
        # HippoRAG-style node specificity: weight each seed by INVERSE degree
        # so generic, highly-connected hubs (e.g. a ubiquitous skill) don't
        # dominate the random walk, while specific/rare seeds steer it.
        # s(node) = 1 / ln(e + degree)  →  1.0 at degree 0, decaying for hubs.
        # https://arxiv.org/abs/2405.14831
        personalization = [0.0] * snapshot.graph.vcount()
        weighted = 0
        for seed_id in seeds:
            idx = snapshot.id_to_idx.get(seed_id)
            if idx is not None:
                degree = snapshot.graph.degree(idx)
                personalization[idx] = 1.0 / math.log(math.e + degree)
                weighted += 1
        if weighted == 0:
            return []

        # igraph 0.11+ exposes `personalized_pagerank`; older releases
        # use `pagerank(reset=personalization)`. We try both.
        try:
            scores = snapshot.graph.personalized_pagerank(reset=personalization)
        except AttributeError:
            scores = snapshot.graph.pagerank(reset=personalization)

        items: list[ScoredItem] = []
        for idx, score in enumerate(scores):
            entity_id, kind, name = snapshot.idx_to_meta[idx]
            if kinds is not None and kind not in kinds:
                continue
            items.append(
                ScoredItem(
                    entity_id=entity_id,
                    kind=kind,
                    name=name,
                    score=float(score),
                    lane=self.name,
                )
            )
        items.sort(key=lambda x: x.score, reverse=True)
        # Exclude the seeds themselves — they're already known.
        seed_set = set(seeds)
        items = [i for i in items if i.entity_id not in seed_set]
        return _attach_ranks(items[:top_k], lane=self.name)


async def _pick_seeds_via_dense(
    session: AsyncSession, user_id: UUID, query: str
) -> list[UUID]:
    """Top-3 dense matches over the user's entities, used as PPR seeds."""
    from src.graph.application.retrieval.dense import DenseRetriever

    retriever = DenseRetriever()
    hits = await retriever.retrieve(session, user_id, query, top_k=3)
    return [h.entity_id for h in hits if h.score > 0.5]
