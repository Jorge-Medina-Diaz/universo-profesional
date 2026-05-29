"""Unit tests: document template rendering, PDF and DOCX generation.

The renderer now returns a storage *key* (relative path) and writes through the
configured storage backend (filesystem in tests). We point storage_root at a
tmp dir and clear the cached storage adapter so each test is isolated.
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from src.documents.infrastructure.renderer import WeasyPrintRenderer
from src.shared.config import get_settings
from src.shared.storage import get_storage


@pytest.fixture
def storage_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(get_settings(), "storage_provider", "filesystem")
    monkeypatch.setattr(get_settings(), "storage_root", tmp_path)
    get_storage.cache_clear()  # rebuild the adapter against tmp_path
    yield tmp_path
    get_storage.cache_clear()


@pytest.fixture
def sample_resume() -> dict:
    return {
        "basics": {
            "name": "Jane Doe",
            "label": "Senior Backend Engineer",
            "email": "jane@example.com",
            "summary": "Experienced Python developer.",
        },
        "work": [
            {
                "name": "Acme",
                "position": "Senior Engineer",
                "startDate": "2020-01",
                "endDate": "2023-06",
                "summary": "Built APIs.",
                "highlights": ["3x throughput"],
            }
        ],
        "education": [
            {
                "institution": "MIT",
                "studyType": "BSc",
                "area": "CS",
                "startDate": "2015-09",
                "endDate": "2019-06",
            }
        ],
        "skills": [{"name": "Python"}, {"name": "FastAPI"}],
        "projects": [{"name": "OpenSource", "description": "Cool project"}],
        "languages": [{"language": "English", "fluency": "Native"}],
    }


@pytest.mark.asyncio
async def test_render_pdf_creates_file(sample_resume: dict, storage_tmp: Path) -> None:
    renderer = WeasyPrintRenderer()
    user_id = uuid4()
    key = await renderer.render_pdf(
        content_json=sample_resume, template="ats-classic", language="en", user_id=user_id
    )
    assert key.startswith(f"{user_id}/")
    assert Path(key).suffix in (".pdf", ".html")
    assert (storage_tmp / key).exists()  # noqa: ASYNC240


@pytest.mark.asyncio
async def test_render_docx_creates_file(sample_resume: dict, storage_tmp: Path) -> None:
    renderer = WeasyPrintRenderer()
    user_id = uuid4()
    key = await renderer.render_docx(
        content_json=sample_resume, template="ats-classic", language="en", user_id=user_id
    )
    assert key.endswith(".docx")
    assert (storage_tmp / key).exists()  # noqa: ASYNC240


@pytest.mark.asyncio
async def test_render_cover_letter_docx(sample_resume: dict, storage_tmp: Path) -> None:
    renderer = WeasyPrintRenderer()
    user_id = uuid4()
    cover_letter = {
        "basics": {"name": "Jane Doe", "email": "jane@example.com"},
        "meta": {"target_company": "Acme", "target_title": "Engineer"},
        "cover_letter_body": "Dear hiring manager,\n\nI am excited...",
    }
    key = await renderer.render_docx(
        content_json=cover_letter, template="cover-letter-classic", language="en", user_id=user_id
    )
    assert key.endswith(".docx")
    assert (storage_tmp / key).exists()  # noqa: ASYNC240


@pytest.mark.asyncio
async def test_render_pdf_fallback_on_bad_template(sample_resume: dict, storage_tmp: Path) -> None:
    renderer = WeasyPrintRenderer()
    user_id = uuid4()
    key = await renderer.render_pdf(
        content_json=sample_resume, template="nonexistent-template", language="en", user_id=user_id
    )
    assert (storage_tmp / key).exists()  # noqa: ASYNC240
