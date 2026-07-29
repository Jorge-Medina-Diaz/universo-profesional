"""Unit tests for notes domain entities."""
from __future__ import annotations

from uuid import uuid4

import pytest
from src.notes.domain.entities import Note
from src.shared.errors import ValidationError


class TestNote:
    def test_create_valid(self):
        n = Note.create(user_id=uuid4(), body_md="Hello")
        assert n.body_md == "Hello"
        assert n.tags == []

    def test_create_with_tags(self):
        n = Note.create(user_id=uuid4(), body_md="Hello", tags=["  A  ", "b"])
        assert n.tags == ["a", "b"]

    def test_create_empty_body_raises(self):
        with pytest.raises(ValidationError):
            Note.create(user_id=uuid4(), body_md="  ")

    def test_embedding_text(self):
        n = Note.create(user_id=uuid4(), body_md="Hello", title="T", tags=["a"])
        text = n.embedding_text()
        assert "T" in text
        assert "Hello" in text
        assert "a" in text

    def test_embedding_text_no_title(self):
        n = Note.create(user_id=uuid4(), body_md="Hello")
        assert n.embedding_text() == "Hello"
