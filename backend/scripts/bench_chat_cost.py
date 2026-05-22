"""Chat token/cost benchmark.

Two modes:

  • Default (offline): aggregate the per-run token metrics that Agno already
    persists into `ai.agno_sessions.runs[].metrics` — input / output / cache
    tokens per run — and print totals, per-run averages, and a rough USD
    estimate. This is how we quantify the savings from model tiering and the
    slimmed coordinator prompt without spending a cent.

  • --live "<message>" : send one real turn through the coordinator team and
    print `result.metrics` (needs ANTHROPIC_API_KEY / OPENAI_API_KEY).

Usage:
    python -m scripts.bench_chat_cost
    python -m scripts.bench_chat_cost --user <uuid>
    python -m scripts.bench_chat_cost --live "¿qué cubre mi backend?" --user <uuid>
"""
from __future__ import annotations

import argparse
import asyncio
from typing import Any

from sqlalchemy import text

from src.shared.db import dispose_engine, get_session_factory

# Rough public list prices (USD per 1M tokens), Anthropic, early 2026. These
# are ASSUMPTIONS for a ballpark — adjust to your contracted rates. Cache
# reads are ~10% of input; cache writes ~125%.
_PRICE_PER_MTOK = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0, "cache_read": 0.10, "cache_write": 1.25},
}
_TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "total_tokens",
)


async def _aggregate_persisted(user_id: str | None) -> dict[str, Any]:
    factory = get_session_factory()
    where = "WHERE user_id = :uid" if user_id else ""
    params = {"uid": user_id} if user_id else {}
    async with factory() as session:
        rows = (
            await session.execute(
                text(f"SELECT runs FROM ai.agno_sessions {where}"),  # noqa: S608
                params,
            )
        ).all()

    totals = dict.fromkeys(_TOKEN_FIELDS, 0)
    run_count = 0
    runs_with_metrics = 0
    for row in rows:
        for run in row.runs or []:
            run_count += 1
            metrics = run.get("metrics") if isinstance(run, dict) else None
            if not isinstance(metrics, dict):
                continue
            runs_with_metrics += 1
            for field in _TOKEN_FIELDS:
                try:
                    totals[field] += int(metrics.get(field, 0) or 0)
                except (TypeError, ValueError):
                    pass
    return {
        "sessions": len(rows),
        "runs": run_count,
        "runs_with_metrics": runs_with_metrics,
        "totals": totals,
    }


def _estimate_usd(totals: dict[str, int], model: str) -> float | None:
    price = _PRICE_PER_MTOK.get(model)
    if price is None:
        return None
    return (
        totals["input_tokens"] / 1e6 * price["input"]
        + totals["output_tokens"] / 1e6 * price["output"]
        + totals["cache_read_tokens"] / 1e6 * price["cache_read"]
        + totals["cache_write_tokens"] / 1e6 * price["cache_write"]
    )


async def _run_live(message: str, user_id: str) -> None:
    from src.agents.factory import get_universe_team

    team = get_universe_team()
    result = await team.arun(
        input=message,
        user_id=user_id,
        session_id=f"main-{user_id}",
        stream=False,
    )
    metrics = getattr(result, "metrics", None)
    print("--- live run metrics ---")
    if metrics is None:
        print("no metrics on result (mock provider?)")
        return
    for field in _TOKEN_FIELDS:
        print(f"  {field}: {getattr(metrics, field, 0)}")


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Chat token/cost benchmark")
    parser.add_argument("--user", default=None, help="restrict to one user id")
    parser.add_argument("--live", default=None, help="send one real turn and report its metrics")
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-6",
        help="model id for the USD estimate (default: coordinator model)",
    )
    args = parser.parse_args()

    try:
        if args.live:
            if not args.user:
                parser.error("--live requires --user <uuid>")
            await _run_live(args.live, args.user)
            return

        agg = await _aggregate_persisted(args.user)
        totals = agg["totals"]
        print("=== Persisted chat token usage ===")
        print(f"sessions: {agg['sessions']}  runs: {agg['runs']}  "
              f"(with metrics: {agg['runs_with_metrics']})")
        for field in _TOKEN_FIELDS:
            print(f"  {field}: {totals[field]:,}")
        if agg["runs_with_metrics"]:
            avg_in = totals["input_tokens"] / agg["runs_with_metrics"]
            avg_out = totals["output_tokens"] / agg["runs_with_metrics"]
            print(f"  avg input/run: {avg_in:,.0f}   avg output/run: {avg_out:,.0f}")
        usd = _estimate_usd(totals, args.model)
        if usd is not None:
            print(f"  est. cost @ {args.model}: ${usd:,.4f} "
                  "(assumed list prices — adjust to your rates)")
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())
