"""Unit tests for document use cases with mocked repositories (no DB)."""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from src.documents.application.use_cases import (
    GetDocument,
    ListDocuments,
    ShareDocument,
)


def _doc(**overrides):
    defaults = {
        "id": uuid4(),
        "user_id": uuid4(),
        "kind": "cv",
        "template": "ats-classic",
        "language": "es",
        "tone": "professional",
        "length": "1-page",
        "job_id": uuid4(),
        "generated_from": {"retrieved": [{"entity_type": "skill", "entity_id": uuid4()}]},
        "content_json": {},
        "pdf_path": "/tmp/x.pdf",
        "docx_path": "/tmp/x.docx",
        "share_token": None,
        "share_expires_at": None,
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestListDocuments:
    async def test_empty(self):
        repo = MagicMock()
        repo.list = AsyncMock(return_value=[])
        uc = ListDocuments(repo)
        result = await uc.execute(user_id=str(uuid4()))
        assert result == []

    async def test_with_items(self):
        d = _doc()
        repo = MagicMock()
        repo.list = AsyncMock(return_value=[d])
        uc = ListDocuments(repo)
        result = await uc.execute(user_id=str(d.user_id))
        assert len(result) == 1
        assert result[0]["id"] == str(d.id)
        assert result[0]["has_pdf"] is True
        assert result[0]["source_entity_ids"]

    async def test_filter_by_kind(self):
        repo = MagicMock()
        repo.list = AsyncMock(return_value=[])
        uc = ListDocuments(repo)
        await uc.execute(user_id=str(uuid4()), kind="cv")
        repo.list.assert_awaited_once()


class TestGetDocument:
    async def test_not_found(self):
        repo = MagicMock()
        repo.get = AsyncMock(return_value=None)
        uc = GetDocument(repo)
        result = await uc.execute(user_id=str(uuid4()), document_id=str(uuid4()))
        assert result.is_failure

    async def test_found(self):
        d = _doc()
        repo = MagicMock()
        repo.get = AsyncMock(return_value=d)
        uc = GetDocument(repo)
        result = await uc.execute(user_id=str(d.user_id), document_id=str(d.id))
        assert result.is_success
        assert result.value["id"] == str(d.id)


class TestShareDocument:
    async def test_not_found(self):
        repo = MagicMock()
        repo.get = AsyncMock(return_value=None)
        uc = ShareDocument(repo)
        result = await uc.execute(user_id=str(uuid4()), document_id=str(uuid4()))
        assert result.is_failure

    async def test_success(self):
        d = _doc()
        repo = MagicMock()
        repo.get = AsyncMock(return_value=d)
        repo.set_share_token = AsyncMock()
        uc = ShareDocument(repo)
        result = await uc.execute(user_id=str(d.user_id), document_id=str(d.id))
        assert result.is_success
        assert result.value["share_token"]
        assert result.value["share_url"]
        repo.set_share_token.assert_awaited_once()
