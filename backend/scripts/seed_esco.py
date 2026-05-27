"""Seed ESCO data into the database automatically.

Usage:
    python -m scripts.seed_esco
    python -m scripts.seed_esco --force
    python -m scripts.seed_esco --sample-only

Environment:
    AUTO_SEED_ESCO        - if "true", skip idempotency checks (default false).
    ESCO_DOWNLOAD_URL     - URL of the ESCO CSV zip bundle.
    ESCO_VERSION          - release tag to record in graph_ingest_meta.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import dataclasses
import os
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import structlog
from sqlalchemy import text
from src.graph.infrastructure.ontology_loader import (
    configure_cli_logging,
    ingest_esco,
)
from src.shared.db import dispose_engine, get_session_factory

csv.field_size_limit(sys.maxsize)

logger = structlog.get_logger(__name__)

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "esco_sample"
DEFAULT_DOWNLOAD_URL = (
    "https://ec.europa.eu/esco/download/"
    "ESCO%20dataset%20-%20v1.1.1%20-%20classification%20-%20en%20-%20csv.zip"
)
MIN_OCCUPATIONS = 1000


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------


def _normalize(text_value: str | None) -> str | None:
    if text_value is None:
        return None
    text_value = text_value.lower().strip()
    # Decompose accents and strip combining chars
    text_value = "".join(
        ch for ch in unicodedata.normalize("NFD", text_value) if unicodedata.category(ch) != "Mn"
    )
    # Collapse whitespace
    return " ".join(text_value.split())


def _normalize_csv_row(row: dict[str, str], text_fields: set[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in row.items():
        if key in text_fields:
            out[key] = _normalize(value) or ""
        else:
            out[key] = value
    return out


def _dedupe_alt_labels(raw: str) -> str:
    if not raw:
        return ""
    parts = [s.strip() for s in raw.replace("\r", "").split("\n") if s.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return "\n".join(out)


def _normalize_dir(src: Path, dest: Path) -> None:
    """Copy CSVs from src to dest with normalised text."""
    dest.mkdir(parents=True, exist_ok=True)
    for csv_path in src.glob("*.csv"):
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            rows = list(reader)

        # Heuristic: text fields we want to normalise
        text_fields = {
            fn
            for fn in fieldnames
            if fn
            in {
                "preferredLabel",
                "altLabels",
                "description",
                "skillType",
                "label_es",
                "label_en",
            }
        }

        out_rows: list[dict[str, str]] = []
        for csv_row in rows:
            norm_row = _normalize_csv_row(csv_row, text_fields)
            if "altLabels" in norm_row:
                norm_row["altLabels"] = _dedupe_alt_labels(norm_row.get("altLabels", ""))
            out_rows.append(norm_row)

        out_path = dest / csv_path.name
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(out_rows)


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def _download_esco_zip(url: str, dest: Path) -> bool:
    """Download ESCO zip to dest; return True on success."""
    logger.info("esco_download_start", url=url)
    try:
        with urlopen(url, timeout=60) as resp:  # noqa: S310
            if resp.status != 200:
                logger.warning("esco_download_http_error", status=resp.status)
                return False
            data = resp.read()
        zip_path = dest / "esco.zip"
        zip_path.write_bytes(data)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest)
        logger.info("esco_download_complete", bytes=len(data))
        return True
    except (HTTPError, URLError, TimeoutError, zipfile.BadZipFile) as exc:
        logger.warning("esco_download_failed", error=str(exc))
        return False


def _find_csv_root(base: Path) -> Path | None:
    """Locate the folder inside base that contains the expected CSVs."""
    for csv_dir in [base, *base.iterdir()]:
        if not csv_dir.is_dir():
            continue
        if (csv_dir / "occupations_en.csv").exists() and (csv_dir / "skills_en.csv").exists():
            return csv_dir
    return None


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


async def _already_seeded(session_factory: Any) -> bool:
    async with session_factory() as session:
        result = await session.execute(
            text("SELECT count(*) FROM ontology_search WHERE label = 'Occupation'")
        )
        count = result.scalar_one()
        return count > MIN_OCCUPATIONS


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def _run(*, force: bool, sample_only: bool) -> None:
    configure_cli_logging()

    session_factory = get_session_factory()

    if not force and not sample_only:
        auto_seed = os.getenv("AUTO_SEED_ESCO", "").lower() in ("1", "true", "yes")
        if not auto_seed:
            seeded = await _already_seeded(session_factory)
            if seeded:
                logger.info("esco_seed_skipped", reason="already_seeded")
                return

    # Determine source directory
    esco_dir: Path | None = None
    if sample_only:
        esco_dir = SAMPLE_DIR
    else:
        download_url = os.getenv("ESCO_DOWNLOAD_URL") or DEFAULT_DOWNLOAD_URL
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            if _download_esco_zip(download_url, tmp):
                found = _find_csv_root(tmp)
                if found:
                    esco_dir = found
                else:
                    logger.warning("esco_csv_not_found_in_zip", fallback="sample")
                    esco_dir = SAMPLE_DIR
            else:
                logger.warning("esco_download_failed", fallback="sample")
                esco_dir = SAMPLE_DIR

            if esco_dir is not None:
                # Normalise into a second temp dir so we don't mutate the sample
                norm_tmp = tmp / "normalized"
                _normalize_dir(esco_dir, norm_tmp)
                esco_dir = norm_tmp

            await _ingest(esco_dir, force, session_factory)
        return

    if esco_dir is None:
        logger.error("esco_no_source")
        raise SystemExit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        norm_tmp = Path(tmpdir) / "normalized"
        _normalize_dir(esco_dir, norm_tmp)
        await _ingest(norm_tmp, force, session_factory)


async def _ingest(esco_dir: Path, force: bool, session_factory: Any) -> None:
    async with session_factory() as session:
        release_tag = os.getenv("ESCO_VERSION", "auto")
        stats = await ingest_esco(
            session,
            esco_dir,
            force=force,
            release_tag=release_tag if release_tag != "auto" else None,
        )
        await session.commit()
    d = dataclasses.asdict(stats)
    d.pop("skipped", None)
    logger.info("esco_seed_done", skipped=stats.skipped, **d)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed ESCO ontology data")
    parser.add_argument("--force", action="store_true", help="Re-seed even if already present")
    parser.add_argument("--sample-only", action="store_true", help="Use bundled sample only")
    args = parser.parse_args()

    try:
        asyncio.run(_run(force=args.force, sample_only=args.sample_only))
    finally:
        asyncio.run(dispose_engine())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
