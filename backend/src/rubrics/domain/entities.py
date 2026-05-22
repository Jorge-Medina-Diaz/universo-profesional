"""Rubric domain — RubricDocument + RubricChunk dataclasses.

These are the in-process representations used by the ingest pipeline and
the agent tools. They map 1:1 with `rubric_documents` and `rubric_chunks`
ORM rows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


# Canonical section kinds. Anything else falls into "general".
SECTION_KINDS = {
    "criteria",
    "questions",
    "signals",
    "anti_patterns",
    "resources",
    "general",
}


@dataclass
class RubricChunk:
    chunk_index: int
    section_kind: str
    heading: str | None
    body_md: str
    sector: str
    tags: list[str] = field(default_factory=list)
    id: UUID | None = None
    document_id: UUID | None = None
    embedding: list[float] | None = None


@dataclass
class RubricDocument:
    slug: str
    sector: str
    title: str
    body_md: str
    content_hash: str
    subtitle: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] | None = None
    version: int = 1
    embedding: list[float] | None = None
    chunks: list[RubricChunk] = field(default_factory=list)
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
