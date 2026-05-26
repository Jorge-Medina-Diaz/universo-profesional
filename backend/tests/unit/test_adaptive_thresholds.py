"""Unit tests for adaptive upsert thresholds.

When a user historically accepts >90 % of merges in the 0.82-0.90 band,
the floor for ambiguous suggestions (AMBIGUOUS_LOW) is lowered.
"""
from __future__ import annotations

from unittest.mock import MagicMock
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
    session = MagicMock()
    session.execute.return_value.all.return_value = []
    result = await _adaptive_ambiguous_low(session, str(uuid4()))
    assert result == AMBIGUOUS_LOW


@pytest.mark.asyncio
async def test_adaptive_low_lowers_for_accepting_user() -> None:
    session = MagicMock()
    # 10 recent merges, 9 in the 0.82-0.90 band → 90 % acceptance signal.
    reasons = [
        _FakeRow("upsert: merged via rules [semantic 0.85]") for _ in range(9)
    ] + [_FakeRow("upsert: merged via rules [semantic 0.95]")]
    session.execute.return_value.all.return_value = reasons
    result = await _adaptive_ambiguous_low(session, str(uuid4()))
    assert result == max(0.70, AMBIGUOUS_LOW - 0.05)


@pytest.mark.asyncio
async def test_adaptive_low_unchanged_for_mixed_user() -> None:
    session = MagicMock()
    # 5 in band, 5 out of band → 50 %, not >90 %.
    reasons = [
        _FakeRow("upsert: merged via rules [semantic 0.85]") for _ in range(5)
    ] + [
        _FakeRow("upsert: merged via rules [semantic 0.95]") for _ in range(5)
    ]
    session.execute.return_value.all.return_value = reasons
    result = await _adaptive_ambiguous_low(session, str(uuid4()))
    assert result == AMBIGUOUS_LOW


@pytest.mark.asyncio
async def test_adaptive_low_ignores_unparseable_reasons() -> None:
    session = MagicMock()
    reasons = [
        _FakeRow(None),
        _FakeRow("upsert: new entity"),
        _FakeRow("upsert: merged via rules [semantic 0.88]"),
    ]
    session.execute.return_value.all.return_value = reasons
    result = await _adaptive_ambiguous_low(session, str(uuid4()))
    # Only 1 parseable score and it is in band → 100 % of parseable scores.
    # But 1/1 > 0.90, so it should lower.
    assert result == max(0.70, AMBIGUOUS_LOW - 0.05)
