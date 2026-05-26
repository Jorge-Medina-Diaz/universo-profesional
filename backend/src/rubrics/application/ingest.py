"""Rubrics ingestion orchestrator.

Walks `<root>/<sector>/<slug>.md`, parses each file, embeds the body + all
chunks, and upserts into the database. Idempotent: re-running with no
changes is a no-op (matches `content_hash`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from src.rubrics.application.markdown_parser import parse_rubric
from src.rubrics.domain.entities import RubricDocument
from src.rubrics.infrastructure.repository import RubricRepository
from src.shared.db import get_session_factory
from src.shared.embeddings import EmbeddingsProvider

logger = structlog.get_logger(__name__)


@dataclass
class IngestSummary:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)

    def add_error(self, path: Path, msg: str) -> None:
        self.errors.append(f"{path}: {msg}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
            "files": self.files,
        }


async def ingest_rubrics(
    root: Path,
    embedder: EmbeddingsProvider,
    *,
    force_reembed: bool = False,
    dry_run: bool = False,
) -> IngestSummary:
    summary = IngestSummary()
    files = sorted(root.rglob("*.md"))
    if not files:
        logger.warning("rubrics_ingest_no_files", root=str(root))
        return summary
    factory = get_session_factory()
    async with factory() as session:
        repo = RubricRepository(session)
        for path in files:
            try:
                raw = path.read_text(encoding="utf-8")
                fallback_slug = _slug_from_path(path, root)
                doc = parse_rubric(raw, fallback_slug=fallback_slug)
                summary.files.append(doc.slug)
                existing = await repo.get_by_slug(doc.slug)
                if (
                    existing
                    and existing.content_hash == doc.content_hash
                    and not force_reembed
                ):
                    summary.skipped += 1
                    logger.info("rubrics_ingest_skip", slug=doc.slug)
                    continue
                if dry_run:
                    logger.info("rubrics_ingest_dryrun", slug=doc.slug)
                    summary.created += 0 if existing else 1
                    summary.updated += 1 if existing else 0
                    continue
                await _embed_doc(doc, embedder)
                upserted, was_created = await repo.upsert_document(doc)
                await repo.replace_chunks(upserted.id, doc.chunks)  # type: ignore[arg-type]
                await session.commit()
                if was_created:
                    summary.created += 1
                else:
                    summary.updated += 1
                logger.info(
                    "rubrics_ingest_ok",
                    slug=doc.slug,
                    sector=doc.sector,
                    chunks=len(doc.chunks),
                    created=was_created,
                )
            except Exception as e:
                await session.rollback()
                summary.add_error(path, str(e))
                logger.error("rubrics_ingest_error", path=str(path), error=str(e))
    return summary


async def _embed_doc(doc: RubricDocument, embedder: EmbeddingsProvider) -> None:
    """Compute embeddings for the doc body + each chunk in a single batch."""
    texts = [_doc_text(doc)] + [_chunk_text(c, doc) for c in doc.chunks]
    vectors = await embedder.embed_batch(texts)
    doc.embedding = vectors[0]
    for c, v in zip(doc.chunks, vectors[1:], strict=True):
        c.embedding = v


def _doc_text(doc: RubricDocument) -> str:
    """Whole-document representation for the doc-level embedding."""
    pieces = [doc.title]
    if doc.subtitle:
        pieces.append(doc.subtitle)
    pieces.append(doc.sector)
    if doc.tags:
        pieces.append(" ".join(doc.tags))
    pieces.append(doc.body_md)
    return "\n".join(pieces)


def _chunk_text(chunk, doc: RubricDocument) -> str:
    """Chunk representation — title + heading + body for better retrieval."""
    pieces = [doc.title]
    if chunk.heading:
        pieces.append(chunk.heading)
    pieces.append(chunk.body_md)
    if chunk.tags:
        pieces.append(" ".join(chunk.tags))
    return "\n".join(pieces)


def _slug_from_path(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    return str(rel).replace("\\", "/")
