"""Unit tests for notes use cases with mocked repositories (no DB)."""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.notes.application.use_cases import (
    CreateNote,
    DeleteNote,
    GetNote,
    ListNotes,
    UpdateNote,
)
from src.notes.domain.entities import Note
from src.shared.uow import UnitOfWork


def _note(**overrides):
    defaults = {
        "id": uuid4(),
        "user_id": uuid4(),
        "title": "My note",
        "body_md": "# Hello",
        "tags": ["idea"],
        "source": "test",
        "source_metadata": None,
        "confidence": 1.0,
        "visibility": "private",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "last_reviewed_at": None,
    }
    defaults.update(overrides)
    return Note(**defaults)


class TestCreateNote:
    async def test_success(self):
        repo = MagicMock()
        repo.add = AsyncMock()
        sched = MagicMock()
        sched.enqueue = AsyncMock()
        uc = CreateNote(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await uc.execute(
            user_id=str(uuid4()), payload={"title": "Note", "body_md": "Body"}, uow=uow
        )
        assert result.is_success
        assert result.value["title"] == "Note"

    async def test_validation_error(self):
        repo = MagicMock()
        sched = MagicMock()
        uc = CreateNote(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        # Missing body_md should trigger validation
        result = await uc.execute(
            user_id=str(uuid4()), payload={"title": "Note", "body_md": ""}, uow=uow
        )
        assert result.is_failure


class TestUpdateNote:
    async def test_not_found(self):
        repo = MagicMock()
        repo.get = AsyncMock(return_value=None)
        sched = MagicMock()
        uc = UpdateNote(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        result = await uc.execute(
            user_id=str(uuid4()), note_id=str(uuid4()), patch={"body_md": "New"}, uow=uow
        )
        assert result.is_failure

    async def test_empty_body_rejected(self):
        note = _note()
        repo = MagicMock()
        repo.get = AsyncMock(return_value=note)
        repo.update = AsyncMock()
        sched = MagicMock()
        uc = UpdateNote(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        result = await uc.execute(
            user_id=str(note.user_id), note_id=str(note.id), patch={"body_md": "   "}, uow=uow
        )
        assert result.is_failure

    async def test_success(self):
        note = _note()
        repo = MagicMock()
        repo.get = AsyncMock(return_value=note)
        repo.update = AsyncMock()
        sched = MagicMock()
        sched.enqueue = AsyncMock()
        uc = UpdateNote(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await uc.execute(
            user_id=str(note.user_id),
            note_id=str(note.id),
            patch={"body_md": "Updated", "tags": ["tag1", "tag2"]},
            uow=uow,
        )
        assert result.is_success
        assert note.body_md == "Updated"
        assert note.tags == ["tag1", "tag2"]


class TestListNotes:
    async def test_empty(self):
        repo = MagicMock()
        repo.list = AsyncMock(return_value=[])
        uc = ListNotes(repo)
        result = await uc.execute(user_id=str(uuid4()))
        assert result == []

    async def test_with_items(self):
        note = _note()
        repo = MagicMock()
        repo.list = AsyncMock(return_value=[note])
        uc = ListNotes(repo)
        result = await uc.execute(user_id=str(note.user_id))
        assert len(result) == 1
        assert result[0]["title"] == "My note"


class TestGetNote:
    async def test_not_found(self):
        repo = MagicMock()
        repo.get = AsyncMock(return_value=None)
        uc = GetNote(repo)
        result = await uc.execute(user_id=str(uuid4()), note_id=str(uuid4()))
        assert result.is_failure

    async def test_found(self):
        note = _note()
        repo = MagicMock()
        repo.get = AsyncMock(return_value=note)
        uc = GetNote(repo)
        result = await uc.execute(user_id=str(note.user_id), note_id=str(note.id))
        assert result.is_success
        assert result.value["title"] == "My note"


class TestDeleteNote:
    async def test_not_found(self):
        repo = MagicMock()
        repo.soft_delete = AsyncMock(return_value=False)
        uc = DeleteNote(repo)
        uow = MagicMock(spec=UnitOfWork)
        result = await uc.execute(user_id=str(uuid4()), note_id=str(uuid4()), uow=uow)
        assert result.is_failure

    async def test_success(self):
        note = _note()
        repo = MagicMock()
        repo.soft_delete = AsyncMock(return_value=True)
        uc = DeleteNote(repo)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await uc.execute(user_id=str(note.user_id), note_id=str(note.id), uow=uow)
        assert result.is_success
