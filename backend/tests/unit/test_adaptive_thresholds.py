"""Unit tests for adaptive upsert thresholds.

When a user historically accepts >90 % of merges in the 0.82-0.90 band,
the floor for ambiguous suggestions (AMBIGUOUS_LOW) is lowered.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from src.coherence.application.upsert_use_cases import (
    AMBIGUOUS_LOW,
    _adaptive_ambiguous_low,
)


class _FakeRow:
    def __init__(self, reason: str | None) -> None:
        self.reason = reason


@pytest.mark.asyncio
async def test_adaptive_low_unchanged_when_no_history() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    session.execute.return_value = mock_result
    result = await _adaptive_ambiguous_low(session, str(uuid4()))
    assert result == AMBIGUOUS_LOW


@pytest.mark.asyncio
async def test_adaptive_low_lowers_for_accepting_user() -> None:
    session = AsyncMock()
    # 10 recent merges, all in the 0.82-0.90 band → 100 % acceptance signal.
    reasons = [
        _FakeRow("upsert: merged via rules [semantic 0.85]") for _ in range(10)
    ]
    mock_result = MagicMock()
    mock_result.all.return_value = reasons
    session.execute.return_value = mock_result
    result = await _adaptive_ambiguous_low(session, str(uuid4()))
    assert result == max(0.70, AMBIGUOUS_LOW - 0.05)


@pytest.mark.asyncio
async def test_adaptive_low_unchanged_for_mixed_user() -> None:
    session = AsyncMock()
    # 5 in band, 5 out of band → 50 %, not >90 %.
    reasons = [
        _FakeRow("upsert: merged via rules [semantic 0.85]") for _ in range(5)
    ] + [
        _FakeRow("upsert: merged via rules [semantic 0.95]") for _ in range(5)
    ]
    mock_result = MagicMock()
    mock_result.all.return_value = reasons
    session.execute.return_value = mock_result
    result = await _adaptive_ambiguous_low(session, str(uuid4()))
    assert result == AMBIGUOUS_LOW


@pytest.mark.asyncio
async def test_adaptive_low_ignores_unparseable_reasons() -> None:
    session = AsyncMock()
    reasons = [
        _FakeRow(None),
        _FakeRow("upsert: new entity"),
        _FakeRow("upsert: merged via rules [semantic 0.88]"),
    ]
    mock_result = MagicMock()
    mock_result.all.return_value = reasons
    session.execute.return_value = mock_result
    result = await _adaptive_ambiguous_low(session, str(uuid4()))
    # Only 1 parseable score and it is in band → 100 % of parseable scores.
    # But 1/1 > 0.90, so it should lower.
    assert result == max(0.70, AMBIGUOUS_LOW - 0.05)
