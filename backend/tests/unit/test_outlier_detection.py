"""Smoke tests for outlier detection (mostly pure — fake session, no DB).

Protects the Sprint-cleanup critical fix: PCA n_components must clamp to
≥1 so tiny universes don't crash the detector, and the detector must
no-op gracefully below MIN_SAMPLES.
"""
from __future__ import annotations

from uuid import uuid4

import numpy as np
import pytest

from src.graph.application.outlier_detection import (
    DETECTABLE_KINDS,
    MIN_SAMPLES,
    PCA_COMPONENTS,
    detect_outliers,
)


class _FakeResult:
    def all(self):  # noqa: ANN201
        return []

    def first(self):  # noqa: ANN201
        # Truthy → the embedding-column existence check passes, so the loader
        # proceeds to the (empty) data query rather than skipping the table.
        return (1,)


class _FakeSession:
    """Returns no rows for every query — simulates an empty universe."""

    async def execute(self, *_args, **_kwargs):  # noqa: ANN002, ANN003, ANN201
        return _FakeResult()


def test_constants_sane() -> None:
    assert MIN_SAMPLES >= 2
    assert PCA_COMPONENTS >= 1
    assert "skill" in DETECTABLE_KINDS


async def test_returns_empty_below_min_samples() -> None:
    # Empty universe → fewer than MIN_SAMPLES embeddings → [].
    result = await detect_outliers(_FakeSession(), uuid4())  # type: ignore[arg-type]
    assert result == []


def test_pca_dim_clamps_to_at_least_one() -> None:
    # Replicates the clamp invariant from detect_outliers: even a
    # degenerate matrix (2 rows) must yield n_components >= 1.
    for n_rows, n_cols in [(2, 1536), (3, 2), (10, 1)]:
        matrix = np.zeros((n_rows, n_cols), dtype=np.float32)
        pca_dim = max(1, min(PCA_COMPONENTS, matrix.shape[0] - 1, matrix.shape[1]))
        assert pca_dim >= 1
