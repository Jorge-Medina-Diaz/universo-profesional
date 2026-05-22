"""CLI entry — `python -m src.universe.cli <command>`.

Commands:
  recompute_shapes   Recompute area_strengths for all users.
  recompute_signals  Recompute user_rubric_signals overlay for all users.
  recompute_all      Run both. Use after a bulk import or schema change.
  Idempotent — safe to re-run.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from uuid import UUID

import structlog
from sqlalchemy import select

from src.identity.infrastructure.orm import UserOrm
from src.shared.db import get_session_factory, set_rls_user
from src.universe.application.shape_service import compute_area_strengths
from src.universe.application.signal_extraction import extract_user_signals

logger = structlog.get_logger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="universe", description="Universe maintenance CLI"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("recompute_shapes", help="Recompute area_strengths for all users")
    p_signals = sub.add_parser(
        "recompute_signals", help="Recompute user_rubric_signals for all users"
    )
    p_signals.add_argument("--sector", type=str, default=None)
    sub.add_parser("recompute_all", help="Shapes + signals for all users")
    args = parser.parse_args(argv)

    if args.cmd == "recompute_shapes":
        return asyncio.run(_recompute_shapes())
    if args.cmd == "recompute_signals":
        return asyncio.run(_recompute_signals(args.sector))
    if args.cmd == "recompute_all":
        rc1 = asyncio.run(_recompute_shapes())
        rc2 = asyncio.run(_recompute_signals(None))
        return rc1 or rc2
    parser.error(f"unknown command: {args.cmd}")
    return 2


async def _list_user_ids() -> list[UUID]:
    factory = get_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                select(UserOrm.id).where(UserOrm.deleted_at.is_(None))
            )
        ).scalars().all()
    return list(rows)


async def _recompute_shapes() -> int:
    factory = get_session_factory()
    user_ids = await _list_user_ids()
    print(f"recomputing shapes for {len(user_ids)} users…")
    processed = 0
    errors = 0
    for user_id in user_ids:
        try:
            async with factory() as session:
                await set_rls_user(session, user_id)
                result = await compute_area_strengths(session, user_id)
                await session.commit()
            processed += 1
            print(
                f"  - {user_id} → {result.shape_type} "
                f"(primaries={result.primary_areas}, "
                f"strengths={len(result.strengths)})"
            )
        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"  ! {user_id} → ERROR: {exc}", file=sys.stderr)
    print(f"shapes done. processed={processed} errors={errors}")
    return 0 if errors == 0 else 1


async def _recompute_signals(sector: str | None) -> int:
    factory = get_session_factory()
    user_ids = await _list_user_ids()
    label = f"sector={sector}" if sector else "all sectors"
    print(f"recomputing signals for {len(user_ids)} users ({label})…")
    processed = 0
    errors = 0
    for user_id in user_ids:
        try:
            async with factory() as session:
                await set_rls_user(session, user_id)
                result = await extract_user_signals(session, user_id, sector=sector)
                await session.commit()
            processed += 1
            print(
                f"  - {user_id} → created={result.signals_created} "
                f"updated={result.signals_updated} removed={result.signals_removed} "
                f"by_status={result.by_status}"
            )
        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"  ! {user_id} → ERROR: {exc}", file=sys.stderr)
    print(f"signals done. processed={processed} errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
