"""Ingest the bundled rubric corpus into `rubric_documents` / `rubric_chunks`.

`backend/rubrics/` ships 44 markdown rubrics, and the agent exposes
`search_rubrics` / `list_rubric_sectors` over them (wired into the
`profile_analyst` and `domain_expert` specialists). Every piece existed —
parser, ORM, repository, ingest orchestrator, agent tools — except a caller, so
the corpus was never loaded and `search_rubrics` queried a permanently empty
table. This is that caller.

Idempotent: `ingest_rubrics` skips any document whose content hash is unchanged,
so re-running on every `docker compose up` costs one hash comparison per file.
Use --force to re-embed regardless (e.g. after switching embeddings provider).
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import structlog

from src.rubrics.application.ingest import ingest_rubrics
from src.rubrics.infrastructure.repository import RubricRepository
from src.shared.db import dispose_engine
from src.shared.embeddings import get_embeddings_provider

logger = structlog.get_logger(__name__)

RUBRICS_DIR = Path(__file__).resolve().parent.parent / "rubrics"


async def _run(*, force: bool, dry_run: bool) -> int:
    if not RUBRICS_DIR.is_dir():
        logger.error("rubrics_dir_missing", path=str(RUBRICS_DIR))
        return 1
    summary = await ingest_rubrics(
        RUBRICS_DIR,
        get_embeddings_provider(),
        repo_class=RubricRepository,
        force_reembed=force,
        dry_run=dry_run,
    )
    logger.info(
        "rubrics_seed_done",
        files=len(summary.files),
        created=summary.created,
        updated=summary.updated,
        skipped=summary.skipped,
        errors=len(summary.errors),
    )
    for err in summary.errors:
        logger.error("rubrics_seed_error", detail=err)
    return 1 if summary.errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the rubric corpus")
    parser.add_argument("--force", action="store_true", help="Re-embed even if unchanged")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, write nothing")
    args = parser.parse_args()

    # Dispose inside the same loop — a second asyncio.run() would try to close
    # connections that belong to the first one. Same trap as seed_esco.
    async def _main() -> int:
        try:
            return await _run(force=args.force, dry_run=args.dry_run)
        finally:
            await dispose_engine()

    return asyncio.run(_main())


if __name__ == "__main__":
    raise SystemExit(main())
