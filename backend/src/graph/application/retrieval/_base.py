from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class ScoredItem:
    """One ranked result from a single lane.

    `score` semantics differ per lane (BM25 ts_rank_cd, cosine, PPR mass),
    so it's only used for tie-breaking; the *rank* is what fusion uses.
    """

    entity_id: UUID
    kind: str
    name: str
    score: float
    rank: int = 0
    lane: str = ""
    rationale: str | None = None


@dataclass(slots=True)
class HybridResult:
    """Fused result with full provenance."""

    entity_id: UUID
    kind: str
    name: str
    fused_score: float
    contributions: dict[str, dict[str, float]] = field(default_factory=dict)
    """Map lane → {rank, score} for the lane's contribution. Useful for
    debugging and "why is this here?" UI surfaces."""


class Retriever(Protocol):
    name: str

    async def retrieve(
        self,
        session: AsyncSession,
        user_id: UUID,
        query: str,
        *,
        top_k: int,
        kinds: Iterable[str] | None = ...,
    ) -> list[ScoredItem]: ...
