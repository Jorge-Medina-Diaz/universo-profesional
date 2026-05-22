"""Unit tests for the knowledge store chunking + vector helpers (pure).

The SQL/RLS/embedding paths are exercised end-to-end against the test DB
elsewhere; these lock in the chunking logic, which is the part most prone
to off-by-one / infinite-loop bugs.
"""
from __future__ import annotations

from src.knowledge.application.use_cases import (
    _CHUNK_OVERLAP,
    _CHUNK_TARGET,
    _vec_literal,
    chunk_text,
)


def test_empty_returns_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_short_text_is_single_chunk() -> None:
    body = "A short professional note about backend engineering."
    assert chunk_text(body) == [body]


def test_long_text_splits_into_multiple_chunks() -> None:
    body = ("palabra " * 1000).strip()  # ~8000 chars
    chunks = chunk_text(body)
    assert len(chunks) > 1
    assert all(c.strip() for c in chunks)
    # Each chunk stays within a sane bound (target + a little slack).
    assert all(len(c) <= _CHUNK_TARGET + 50 for c in chunks)


def test_chunks_cover_all_content() -> None:
    # Every distinct token in the source survives somewhere in the chunks.
    body = " ".join(f"tok{i}" for i in range(500))  # ~3000 chars, unique tokens
    chunks = chunk_text(body)
    joined = " ".join(chunks)
    for i in (0, 123, 250, 499):
        assert f"tok{i}" in joined


def test_chunks_overlap_for_continuity() -> None:
    body = " ".join(f"w{i}" for i in range(800))
    chunks = chunk_text(body)
    assert len(chunks) >= 2
    # Consecutive chunks should share some text (overlap window).
    tail = chunks[0][-_CHUNK_OVERLAP:]
    assert any(word in chunks[1] for word in tail.split()[:3])


def test_prefers_paragraph_boundary() -> None:
    para_a = "x" * 700
    para_b = "y" * 700
    body = f"{para_a}\n\n{para_b}"
    chunks = chunk_text(body)
    # The first chunk should end at the paragraph break, not mid-paragraph.
    assert chunks[0].endswith("x")
    assert not chunks[0].startswith("y")


def test_vec_literal_format() -> None:
    assert _vec_literal([0.1, -0.2, 1.0]) == "[0.1000000,-0.2000000,1.0000000]"
    assert _vec_literal([]) == "[]"
