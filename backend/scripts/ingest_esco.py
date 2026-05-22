"""CLI entry point: ingest the ESCO CSV bundle into universe_ontology.

Usage:
    python -m scripts.ingest_esco --esco-dir /app/data/esco
    python -m scripts.ingest_esco --esco-dir /app/data/esco --force
    python -m scripts.ingest_esco --verify

Download the ESCO CSV bundle (v1.2 ES + EN locales) from
https://esco.ec.europa.eu/en/use-esco/download and extract into the
directory passed via --esco-dir. The script is idempotent: it records
the release tag in `graph_ingest_meta` and skips on re-runs.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import structlog
from sqlalchemy import text

from src.graph.domain import schema
from src.graph.infrastructure.age_client import cypher, ensure_age_loaded
from src.graph.infrastructure.ontology_loader import (
    configure_cli_logging,
    ingest_esco,
)
from src.shared.db import dispose_engine, get_session_factory

logger = structlog.get_logger(__name__)


async def _verify_only() -> None:
    factory = get_session_factory()
    async with factory() as session:
        await ensure_age_loaded(session)
        # Counts
        occ = await cypher(
            session,
            schema.GRAPH_ONTOLOGY,
            "MATCH (n:Occupation) RETURN count(n)",
            column_defs="c agtype",
        )
        sk = await cypher(
            session,
            schema.GRAPH_ONTOLOGY,
            "MATCH (n:EscoSkill) RETURN count(n)",
            column_defs="c agtype",
        )
        ig = await cypher(
            session,
            schema.GRAPH_ONTOLOGY,
            "MATCH (n:ISCOGroup) RETURN count(n)",
            column_defs="c agtype",
        )
        emb = await session.execute(text("SELECT count(*) FROM ontology_embeddings"))
        release = await session.execute(
            text("SELECT value FROM graph_ingest_meta WHERE name = 'esco_release_version'")
        )
        print(f"release         : {release.scalar_one_or_none()}")
        print(f"occupations     : {occ}")
        print(f"esco_skills     : {sk}")
        print(f"isco_groups     : {ig}")
        print(f"embeddings rows : {emb.scalar_one()}")


async def _run(esco_dir: Path, *, force: bool, release_tag: str | None) -> None:
    factory = get_session_factory()
    async with factory() as session:
        stats = await ingest_esco(
            session,
            esco_dir,
            force=force,
            release_tag=release_tag,
        )
        await session.commit()
    logger.info("esco_done", **stats.__dict__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest ESCO into universe_ontology")
    parser.add_argument(
        "--esco-dir",
        type=Path,
        default=Path("/app/data/esco"),
        help="Folder containing the extracted ESCO CSV bundle",
    )
    parser.add_argument("--force", action="store_true", help="Re-ingest even if release matches")
    parser.add_argument(
        "--release-tag",
        type=str,
        default=None,
        help="Explicit release tag (e.g. 'v1.2.0'). Defaults to a content hash.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Print current counts instead of ingesting.",
    )
    args = parser.parse_args()

    configure_cli_logging()

    try:
        if args.verify:
            asyncio.run(_verify_only())
        else:
            if not args.esco_dir.exists():
                print(f"ESCO dir not found: {args.esco_dir}", flush=True)
                return 2
            asyncio.run(_run(args.esco_dir, force=args.force, release_tag=args.release_tag))
    finally:
        asyncio.run(dispose_engine())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
