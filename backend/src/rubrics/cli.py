"""CLI entry point — `python -m src.rubrics.cli ingest [...]`."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from src.rubrics.application.ingest import ingest_rubrics
from src.rubrics.infrastructure.repository import RubricRepository
from src.shared.embeddings import get_embeddings_provider


def _default_root() -> Path:
    # backend/src/rubrics/cli.py → backend/rubrics
    return Path(__file__).resolve().parents[2] / "rubrics"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rubrics", description="System rubrics corpus CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ingest = sub.add_parser("ingest", help="Walk markdown files and upsert into DB")
    p_ingest.add_argument(
        "--path",
        type=Path,
        default=_default_root(),
        help="Root directory containing <sector>/<slug>.md files",
    )
    p_ingest.add_argument(
        "--force-reembed",
        action="store_true",
        help="Re-embed even if content_hash matches existing row",
    )
    p_ingest.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse + validate but don't write to DB",
    )

    args = parser.parse_args(argv)

    if args.cmd == "ingest":
        return asyncio.run(_run_ingest(args))
    parser.error(f"unknown command: {args.cmd}")
    return 2


async def _run_ingest(args) -> int:
    root: Path = args.path
    if not root.exists():
        print(f"rubrics root not found: {root}", file=sys.stderr)
        return 1
    embedder = get_embeddings_provider()
    summary = await ingest_rubrics(
        root=root,
        embedder=embedder,
        repo_class=RubricRepository,
        force_reembed=args.force_reembed,
        dry_run=args.dry_run,
    )
    print(
        f"rubrics ingest: created={summary.created} "
        f"updated={summary.updated} skipped={summary.skipped} "
        f"errors={len(summary.errors)} files={len(summary.files)}"
    )
    if summary.errors:
        print("errors:", file=sys.stderr)
        for e in summary.errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
