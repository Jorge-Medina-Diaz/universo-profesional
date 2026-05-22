"""Markdown rubric parser.

Each rubric file under `backend/rubrics/<sector>/<slug>.md` follows this shape:

    ---
    sector: backend
    slug: backend/api_design
    title: "Diseño de APIs"
    subtitle: "Cómo distinguir buen vs mal API design"
    tags: [api, rest, ...]
    weight: high
    audience_levels: [junior, mid, senior, staff]
    when_to_ask:
      - "el usuario menciona endpoints"
    ---

    ## Criterios clave
    ...

    ## Preguntas guía
    ...

We split the body on H2 (`## `) and infer `section_kind` from heading keywords.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

import yaml

from src.rubrics.domain.entities import RubricChunk, RubricDocument

# Keyword → canonical section_kind. First match wins.
SECTION_HEADING_MAP: tuple[tuple[str, str], ...] = (
    ("criterio", "criteria"),
    ("clave", "criteria"),
    ("pregunta", "questions"),
    ("guía", "questions"),
    ("guia", "questions"),
    ("señal", "signals"),
    ("seniority", "signals"),
    ("nivel", "signals"),
    ("anti-pattern", "anti_patterns"),
    ("antipattern", "anti_patterns"),
    ("anti patron", "anti_patterns"),
    ("anti patrón", "anti_patterns"),
    ("anti-patron", "anti_patterns"),
    ("recurso", "resources"),
    ("referencia", "resources"),
    ("lectura", "resources"),
)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def parse_rubric(raw: str, *, fallback_slug: str | None = None) -> RubricDocument:
    """Parse a markdown rubric file into a RubricDocument with chunks."""
    fm_match = FRONTMATTER_RE.match(raw)
    if not fm_match:
        raise ValueError("rubric file is missing frontmatter (--- ... ---)")
    fm_yaml = fm_match.group(1)
    body = raw[fm_match.end() :].strip()
    try:
        fm = yaml.safe_load(fm_yaml) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"invalid YAML frontmatter: {e}") from e
    sector = (fm.get("sector") or "general").strip().lower()
    slug = (fm.get("slug") or fallback_slug or "").strip()
    if not slug:
        raise ValueError("rubric is missing `slug` in frontmatter")
    title = (fm.get("title") or "").strip()
    if not title:
        raise ValueError("rubric is missing `title` in frontmatter")
    subtitle = fm.get("subtitle")
    tags_raw = fm.get("tags") or []
    if isinstance(tags_raw, str):
        tags_raw = [t.strip() for t in tags_raw.split(",")]
    tags = [t.lower().strip() for t in tags_raw if isinstance(t, str) and t.strip()]
    metadata: dict[str, Any] = {
        "weight": fm.get("weight"),
        "audience_levels": fm.get("audience_levels") or [],
        "when_to_ask": fm.get("when_to_ask") or [],
    }
    chunks = _chunk_body(body=body, sector=sector, tags=tags)
    content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return RubricDocument(
        slug=slug,
        sector=sector,
        title=title,
        subtitle=subtitle if isinstance(subtitle, str) else None,
        body_md=body,
        tags=tags,
        metadata=metadata,
        version=int(fm.get("version") or 1),
        content_hash=content_hash,
        chunks=chunks,
    )


def _chunk_body(*, body: str, sector: str, tags: list[str]) -> list[RubricChunk]:
    """Split body on H2 headings; each chunk inherits sector + tags + section_kind."""
    matches = list(H2_RE.finditer(body))
    if not matches:
        return [
            RubricChunk(
                chunk_index=0,
                section_kind="general",
                heading=None,
                body_md=body.strip(),
                sector=sector,
                tags=tags,
            )
        ]
    chunks: list[RubricChunk] = []
    for i, m in enumerate(matches):
        heading = m.group(1).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_body = body[start:end].strip()
        kind = _classify_heading(heading)
        # If chunk too large (> ~800 words), keep as-is for v1; future: paragraph split.
        chunks.append(
            RubricChunk(
                chunk_index=i,
                section_kind=kind,
                heading=heading,
                body_md=section_body,
                sector=sector,
                tags=tags,
            )
        )
    return chunks


def _classify_heading(heading: str) -> str:
    low = heading.lower()
    for needle, kind in SECTION_HEADING_MAP:
        if needle in low:
            return kind
    return "general"
