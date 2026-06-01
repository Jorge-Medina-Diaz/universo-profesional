"""Unit tests for LLM cost tracking."""
from __future__ import annotations

from decimal import Decimal

import pytest
from src.llm_tracking.application.tracker import compute_cost_eur


class TestComputeCostEur:
    @pytest.mark.parametrize(
        ("model", "input_tokens", "output_tokens", "expected"),
        [
            ("claude-sonnet-4-6", 1_000_000, 0, Decimal("3.000000")),
            ("claude-sonnet-4-6", 0, 1_000_000, Decimal("15.000000")),
            ("claude-sonnet-4-6", 1_000_000, 1_000_000, Decimal("18.000000")),
            ("claude-haiku-4-5-20251001", 1_000_000, 0, Decimal("0.250000")),
            ("claude-haiku-4-5-20251001", 0, 1_000_000, Decimal("1.250000")),
            ("gpt-4o", 1_000_000, 0, Decimal("5.000000")),
            ("gpt-4o", 0, 1_000_000, Decimal("15.000000")),
            ("gpt-4o-mini", 1_000_000, 0, Decimal("0.150000")),
            ("gpt-4o-mini", 0, 1_000_000, Decimal("0.600000")),
        ],
    )
    def test_known_models(
        self, model: str, input_tokens: int, output_tokens: int, expected: Decimal
    ) -> None:
        result = compute_cost_eur(
            model=model, input_tokens=input_tokens, output_tokens=output_tokens
        )
        assert result == expected

    def test_unknown_model_returns_none(self) -> None:
        assert compute_cost_eur(model="unknown-model", input_tokens=1000, output_tokens=1000) is None

    def test_dated_slug_resolves_to_base_price(self) -> None:
        # A dated/versioned model id must still resolve (otherwise the cost is
        # silently dropped). claude-sonnet-4-6-20250101 -> the sonnet price.
        assert compute_cost_eur(
            model="claude-sonnet-4-6-20250101", input_tokens=1_000_000, output_tokens=0
        ) == Decimal("3.000000")

    def test_family_shorthand_resolves(self) -> None:
        # The bare family id is a prefix of the dated key and must resolve too.
        assert compute_cost_eur(
            model="claude-haiku-4-5", input_tokens=1_000_000, output_tokens=0
        ) == Decimal("0.250000")

    def test_cache_tokens(self) -> None:
        result = compute_cost_eur(
            model="claude-sonnet-4-6",
            input_tokens=1_000_000,
            output_tokens=0,
            cache_read_tokens=1_000_000,
            cache_write_tokens=1_000_000,
        )
        assert result == Decimal("7.050000")

    def test_small_values(self) -> None:
        result = compute_cost_eur(
            model="gpt-4o-mini", input_tokens=1000, output_tokens=500
        )
        expected = Decimal("0.000450")
        assert result == expected
