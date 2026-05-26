"""Signal extraction — bridge between rubric corpus (global) and user universe (personal).

For each rubric_chunk we maintain at most one `user_rubric_signal` row per user
that captures: how this user relates to that chunk (aspire / practice / own /
teach / avoid), how confident the match is, and which entities sustain it.

The service is invoked:
  - on entry add/update/remove events (debounced 5s) → recompute affected sector.
  - manually via the CLI / agent tool `recompute_user_signals()`.
  - by `tech_radar_specialist` when the cached signals are stale.

Idempotent: running twice with the same universe produces the same signals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from src.rubrics.infrastructure.orm import RubricChunkOrm
from src.shared.embeddings import get_embeddings_service
from src.universe.domain.entities import UserRubricSignal
from src.universe.infrastructure.orm import (
    ArtifactOrm,
    ExperienceOrm,
    ProjectOrm,
    SkillOrm,
)
from src.universe.infrastructure.repositories import (
    SqlAlchemyUserRubricSignalRepository,
)

# Thresholds tuned for production embeddings (OpenAI text-embedding-3-small).
# Deterministic embeddings (dev fallback) produce noise; we still upsert
# in dev but scores are mostly < 0.6 (treated as 'aspire').
THRESHOLD_OWN = 0.78
THRESHOLD_PRACTICE = 0.68
THRESHOLD_ASPIRE = 0.55
ANTI_PATTERN_WARN = 0.72


def _now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass
class SignalExtractionResult:
    user_id: UUID
    sector_filter: str | None
    signals_created: int = 0
    signals_updated: int = 0
    signals_removed: int = 0
    by_status: dict[str, int] = field(default_factory=dict)


async def _load_user_text_blob(
    session: AsyncSession, user_id: UUID
) -> dict[str, list[tuple[UUID, str]]]:
    """Returns evidence pools by entity_type with (id, embedding_text)."""
    pools: dict[str, list[tuple[UUID, str]]] = {
        "skill": [],
        "project": [],
        "experience": [],
        "artifact": [],
    }
    skills = (
        await session.execute(
            select(SkillOrm)
            .where(SkillOrm.user_id == user_id)
            .where(SkillOrm.deleted_at.is_(None))
        )
    ).scalars().all()
    for s in skills:
        text = f"{s.name} {s.category or ''} {s.level or ''} {s.years or ''}".strip()
        if text:
            pools["skill"].append((s.id, text))

    projects = (
        await session.execute(
            select(ProjectOrm)
            .where(ProjectOrm.user_id == user_id)
            .where(ProjectOrm.deleted_at.is_(None))
        )
    ).scalars().all()
    for p in projects:
        stack = " ".join(str(x) for x in (p.tech_stack or []))
        highlights = " ".join(str(x) for x in (p.highlights or []))
        tags = " ".join(p.domain_tags or [])
        text = f"{p.name} {p.description or ''} {stack} {highlights} {tags}".strip()
        if text:
            pools["project"].append((p.id, text))

    experiences = (
        await session.execute(
            select(ExperienceOrm)
            .where(ExperienceOrm.user_id == user_id)
            .where(ExperienceOrm.deleted_at.is_(None))
        )
    ).scalars().all()
    for e in experiences:
        comp = " ".join(str(c) for c in (e.competences or []))
        hl = " ".join(str(h) for h in (e.highlights or []))
        text = f"{e.role} @ {e.organization} {e.description or ''} {comp} {hl} {e.industry_sector or ''} {e.seniority_level or ''}".strip()
        if text:
            pools["experience"].append((e.id, text))

    artifacts = (
        await session.execute(
            select(ArtifactOrm)
            .where(ArtifactOrm.user_id == user_id)
            .where(ArtifactOrm.deleted_at.is_(None))
        )
    ).scalars().all()
    for a in artifacts:
        text = f"{a.type} {a.title} {a.description or ''} {a.venue or ''}".strip()
        if text:
            pools["artifact"].append((a.id, text))

    return pools


async def _load_rubric_chunks(
    session: AsyncSession, sector: str | None
) -> list[RubricChunkOrm]:
    stmt = select(RubricChunkOrm)
    if sector:
        stmt = stmt.where(RubricChunkOrm.sector == sector)
    return list((await session.execute(stmt)).scalars().all())


def _vec_literal(emb: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in emb) + "]"


async def _score_chunk_vs_pools(
    session: AsyncSession,
    chunk: RubricChunkOrm,
    pools: dict[str, list[tuple[UUID, str]]],
    embedder: Any,
) -> tuple[str, list[UUID], float]:
    """Returns (best_entity_type, [matching_entity_ids], best_score)."""
    if chunk.embedding is None:
        return ("", [], 0.0)
    best_score = 0.0
    best_pool: str = ""
    best_ids: list[UUID] = []
    for entity_type, entries in pools.items():
        if not entries:
            continue
        # Cheap pre-filter: keyword check on chunk body vs pool text.
        chunk_text_lower = (chunk.body_md or "").lower()
        candidates = [(eid, t) for eid, t in entries if _keyword_overlap(t.lower(), chunk_text_lower)]
        if not candidates:
            continue
        # Embed candidates' texts in batch.
        texts = [t for _, t in candidates]
        try:
            embs = await embedder.embed_batch(texts)
        except Exception:
            embs = [await embedder.embed(t) for t in texts]
        # Cosine vs chunk.embedding (already a list[float] via pgvector)
        chunk_vec = list(chunk.embedding)
        for (eid, _t), evec in zip(candidates, embs, strict=False):
            score = _cosine(chunk_vec, evec)
            if score > best_score:
                best_score = score
                best_pool = entity_type
                best_ids = [eid]
            elif score >= best_score - 0.02 and best_pool == entity_type:
                # Group near-ties from same pool as co-evidence.
                best_ids.append(eid)
    return (best_pool, best_ids, best_score)


def _keyword_overlap(a: str, b: str) -> bool:
    # 2+ shared "words" of length >= 4 = candidate.
    words_a = {w for w in a.split() if len(w) >= 4}
    words_b = {w for w in b.split() if len(w) >= 4}
    return len(words_a & words_b) >= 2


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _classify_status(section_kind: str, score: float) -> str | None:
    """Map (section_kind, score) → user_rubric_signal.status. Return None to skip."""
    if section_kind == "anti_patterns":
        if score >= ANTI_PATTERN_WARN:
            return "avoid"  # warning: user is doing the anti-pattern
        return None
    # Default for criteria/signals/questions/resources/general
    if score >= THRESHOLD_OWN:
        return "own"
    if score >= THRESHOLD_PRACTICE:
        return "practice"
    if score >= THRESHOLD_ASPIRE:
        return "aspire"
    return None


async def extract_user_signals(
    session: AsyncSession,
    user_id: UUID,
    *,
    sector: str | None = None,
) -> SignalExtractionResult:
    embedder = get_embeddings_service()
    pools = await _load_user_text_blob(session, user_id)
    if not any(pools.values()):
        return SignalExtractionResult(user_id=user_id, sector_filter=sector)
    chunks = await _load_rubric_chunks(session, sector)
    repo = SqlAlchemyUserRubricSignalRepository(session)
    existing_rows = await repo.list(user_id)
    existing_by_chunk: dict[UUID, UserRubricSignal] = {
        r.rubric_chunk_id: r for r in existing_rows
    }

    result = SignalExtractionResult(user_id=user_id, sector_filter=sector)
    kept_chunk_ids: set[UUID] = set()

    for chunk in chunks:
        pool, ids, score = await _score_chunk_vs_pools(session, chunk, pools, embedder)
        status = _classify_status(chunk.section_kind, score)
        if status is None:
            continue
        kept_chunk_ids.add(chunk.id)
        signal = UserRubricSignal.create(
            user_id=user_id,
            rubric_chunk_id=chunk.id,
            section_kind=chunk.section_kind,
            status=status,
            confidence=round(min(1.0, max(0.0, score)), 2),
            evidence_entity_type=pool or None,
            evidence_entity_ids=ids[:5],  # cap to 5 for sanity
            source="auto",
        )
        # Preserve existing id (so change_log threads correctly) when present.
        if chunk.id in existing_by_chunk:
            prev = existing_by_chunk[chunk.id]
            signal.id = prev.id
            signal.created_at = prev.created_at
            signal.last_reviewed_at = prev.last_reviewed_at
        _, created = await repo.upsert(signal)
        if created:
            result.signals_created += 1
        else:
            result.signals_updated += 1
        result.by_status[status] = result.by_status.get(status, 0) + 1

    # Soft-delete signals for chunks that no longer have evidence (in this sector
    # scope). If sector is None we sweep all; if scoped, only chunks within the
    # sector that disappeared.
    chunks_in_scope = {c.id for c in chunks}
    to_remove = [
        cid for cid in existing_by_chunk
        if cid in chunks_in_scope and cid not in kept_chunk_ids
    ]
    if to_remove:
        result.signals_removed = await repo.delete_for_chunks(user_id, to_remove)

    return result


async def list_user_signals_with_chunk(
    session: AsyncSession,
    user_id: UUID,
    *,
    sector: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Join user_rubric_signals × rubric_chunks for display purposes."""
    where_parts = ["urs.user_id = :uid", "urs.deleted_at IS NULL"]
    params: dict[str, Any] = {"uid": str(user_id)}
    if sector:
        where_parts.append("rc.sector = :sector")
        params["sector"] = sector
    if status:
        where_parts.append("urs.status = :status")
        params["status"] = status
    where_sql = " AND ".join(where_parts)
    stmt = sql_text(
        f"""
        SELECT
            urs.id AS signal_id,
            urs.rubric_chunk_id,
            urs.section_kind,
            urs.status,
            urs.confidence,
            urs.evidence_entity_type,
            urs.evidence_entity_ids,
            urs.last_reviewed_at,
            urs.updated_at,
            rc.sector,
            rc.heading,
            rc.body_md,
            rd.slug AS rubric_slug,
            rd.title AS rubric_title
        FROM user_rubric_signals urs
        JOIN rubric_chunks rc ON rc.id = urs.rubric_chunk_id
        JOIN rubric_documents rd ON rd.id = rc.document_id
        WHERE {where_sql}
        ORDER BY urs.confidence DESC, urs.updated_at DESC
        """
    )
    rows = (await session.execute(stmt, params)).mappings().all()
    return [dict(r) for r in rows]
