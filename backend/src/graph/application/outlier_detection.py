"""Outlier detection over a user's entity embeddings.

Flags entities whose embedding sits outside the user's typical distribution
— a strong signal of either a mis-extraction (e.g., the agent recorded
"molecular cooking" for a backend engineer) or a genuine new direction
the curator should ask about.

Pipeline (per user, per coherence pass):

  1. Load all active entity embeddings for the user (skills + projects +
     experiences + artifacts — the entity kinds with rich text).
  2. Project to 64-d with PCA (raw 1536-d makes covariance noisy and
     the small-n regime kills Mahalanobis).
  3. Run two detectors in parallel:
       • IsolationForest — robust, global, low memory.
       • LOF — local density, good when the universe has multiple
         distinct clusters (most polyglot profiles do).
  4. Flag the entity as outlier iff *both* detectors agree.

We deliberately do NOT auto-delete or auto-merge outliers. The flag goes
into `entity_quarantine` with reason="outlier" so the chat coordinator
can ask the user. See `mark_outlier()`.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import numpy as np
import structlog
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


# Process-lifetime cache of table → has-embedding-column. Schema only changes
# via migrations (which restart workers), so caching is safe.
_EMBEDDING_TABLE_CACHE: dict[str, bool] = {}


async def _table_has_embedding(session: AsyncSession, table: str) -> bool:
    cached = _EMBEDDING_TABLE_CACHE.get(table)
    if cached is not None:
        return cached
    row = (
        await session.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = :t AND column_name = 'embedding'"
            ),
            {"t": table},
        )
    ).first()
    exists = row is not None
    _EMBEDDING_TABLE_CACHE[table] = exists
    return exists


# Entity kinds whose embeddings we feed into the detector. These have
# enough text behind them to produce stable vectors; certifications and
# languages have very terse labels that would dominate the variance.
DETECTABLE_KINDS: tuple[str, ...] = (
    "skill",
    "project",
    "experience",
    "artifact",
    "achievement",
    "architecture_decision",
)

# Detector parameters — tuned for ~50-500 nodes per user.
PCA_COMPONENTS = 64
ISOFOREST_CONTAMINATION = 0.05  # expect ≤5% outliers in a typical universe
LOF_N_NEIGHBORS = 10
MIN_SAMPLES = 8                  # below this, all detectors are unreliable


@dataclass(slots=True)
class OutlierResult:
    entity_id: UUID
    kind: str
    iso_forest_score: float    # higher is more anomalous
    lof_score: float
    is_outlier: bool


async def detect_outliers(
    session: AsyncSession,
    user_id: UUID,
    *,
    kinds: tuple[str, ...] = DETECTABLE_KINDS,
) -> list[OutlierResult]:
    """Run the IsoForest + LOF ensemble over the user's embeddings.

    Returns one OutlierResult per inspected entity. `is_outlier` is True
    only when both detectors agree, so the false-positive rate stays low.
    """
    embeddings, ids, kind_for_id = await _load_user_embeddings(
        session, user_id, kinds
    )
    if len(embeddings) < MIN_SAMPLES:
        return []

    matrix = np.asarray(embeddings, dtype=np.float32)
    # Clamp pca_dim ≥ 1 — when the dataset is tiny (~few rows or low-d),
    # min() can yield 0 or negative, which crashes PCA. We guard explicitly
    # so the detector degrades gracefully rather than throwing.
    pca_dim = max(1, min(PCA_COMPONENTS, matrix.shape[0] - 1, matrix.shape[1]))
    reducer = PCA(n_components=pca_dim, random_state=42)
    reduced = reducer.fit_transform(matrix)

    iso = IsolationForest(
        contamination=ISOFOREST_CONTAMINATION,
        random_state=42,
        n_estimators=100,
    )
    iso.fit(reduced)
    # `decision_function` is positive for inliers, negative for outliers.
    iso_decision = iso.decision_function(reduced)
    iso_flag = iso.predict(reduced) == -1

    # LOF requires at least n_neighbors + 1 samples. Cap dynamically.
    n_neighbors = min(LOF_N_NEIGHBORS, len(reduced) - 1)
    lof = LocalOutlierFactor(n_neighbors=n_neighbors)
    lof_flag = lof.fit_predict(reduced) == -1
    lof_scores = -lof.negative_outlier_factor_  # higher = more anomalous

    results = []
    for idx, entity_id in enumerate(ids):
        results.append(
            OutlierResult(
                entity_id=entity_id,
                kind=kind_for_id[entity_id],
                iso_forest_score=float(-iso_decision[idx]),
                lof_score=float(lof_scores[idx]),
                is_outlier=bool(iso_flag[idx] and lof_flag[idx]),
            )
        )
    return results


async def mark_outlier(
    session: AsyncSession,
    *,
    user_id: UUID,
    entity_id: UUID,
    kind: str,
    iso_score: float,
    lof_score: float,
) -> None:
    """Persist an outlier flag into entity_quarantine.

    Idempotent — re-running the detector should not create duplicate
    rows for an already-pending outlier on the same entity.
    """
    await session.execute(
        text(
            """
            INSERT INTO entity_quarantine
                (user_id, entity_id, kind, reason, candidates, notes)
            SELECT :uid, :eid, :kind, 'outlier', '[]'::jsonb, :notes
            WHERE NOT EXISTS (
                SELECT 1 FROM entity_quarantine
                 WHERE user_id = :uid
                   AND entity_id = :eid
                   AND reason = 'outlier'
                   AND resolved_at IS NULL
            )
            """
        ),
        {
            "uid": str(user_id),
            "eid": str(entity_id),
            "kind": kind,
            "notes": f"iso={iso_score:.3f} lof={lof_score:.3f}",
        },
    )


async def _load_user_embeddings(
    session: AsyncSession,
    user_id: UUID,
    kinds: tuple[str, ...],
) -> tuple[list[list[float]], list[UUID], dict[UUID, str]]:
    """Pull (embedding, id, kind) triples from the per-kind SQL tables.

    We read from the authoritative SQL tables (still the source of truth
    until Sprint R cutover). Each kind has its own table; we union them
    into a single result set.
    """
    from src.graph.domain.registry import GRAPH_REGISTRY

    rows: list[tuple[str, list[float], str]] = []
    for kind in kinds:
        cfg = GRAPH_REGISTRY.get(kind)
        if cfg is None:
            continue
        # Some detectable kinds (e.g. artifacts) have no embedding column —
        # they can't contribute to embedding-space outlier detection, so skip
        # them cleanly rather than emitting SQL that references a missing column.
        if not await _table_has_embedding(session, cfg.sql_table):
            continue
        result = await session.execute(
            text(
                f"SELECT id::text AS id, embedding "
                f"FROM {cfg.sql_table} "
                f"WHERE user_id = :uid "
                f"  AND deleted_at IS NULL "
                f"  AND embedding IS NOT NULL"
            ),
            {"uid": str(user_id)},
        )
        for row in result.all():
            # pgvector returns the embedding as a list[float] via psycopg.
            vec = list(row.embedding) if row.embedding is not None else None
            if vec is None:
                continue
            rows.append((row.id, vec, kind))

    embeddings: list[list[float]] = []
    ids: list[UUID] = []
    kind_for_id: dict[UUID, str] = {}
    for raw_id, vec, kind in rows:
        try:
            eid = UUID(raw_id)
        except ValueError:
            continue
        embeddings.append(vec)
        ids.append(eid)
        kind_for_id[eid] = kind
    return embeddings, ids, kind_for_id
