"""Unit tests: document template rendering, PDF and DOCX generation."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from src.documents.infrastructure.renderer import WeasyPrintRenderer, _ensure_user_dir


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
async def test_render_pdf_creates_file(sample_resume: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.shared.config import get_settings

    monkeypatch.setattr(get_settings(), "storage_root", tmp_path)
    renderer = WeasyPrintRenderer()
    user_id = uuid4()
    path = await renderer.render_pdf(
        content_json=sample_resume,
        template="ats-classic",
        language="en",
        user_id=user_id,
    )
    assert Path(path).exists()
    assert Path(path).suffix in (".pdf", ".html")


@pytest.mark.asyncio
async def test_render_docx_creates_file(sample_resume: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.shared.config import get_settings

    monkeypatch.setattr(get_settings(), "storage_root", tmp_path)
    renderer = WeasyPrintRenderer()
    user_id = uuid4()
    path = await renderer.render_docx(
        content_json=sample_resume,
        template="ats-classic",
        language="en",
        user_id=user_id,
    )
    assert Path(path).exists()
    assert Path(path).suffix == ".docx"


@pytest.mark.asyncio
async def test_render_cover_letter_docx(sample_resume: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.shared.config import get_settings

    monkeypatch.setattr(get_settings(), "storage_root", tmp_path)
    renderer = WeasyPrintRenderer()
    user_id = uuid4()
    cover_letter = {
        "basics": {"name": "Jane Doe", "email": "jane@example.com"},
        "meta": {"target_company": "Acme", "target_title": "Engineer"},
        "cover_letter_body": "Dear hiring manager,\n\nI am excited...",
    }
    path = await renderer.render_docx(
        content_json=cover_letter,
        template="cover-letter-classic",
        language="en",
        user_id=user_id,
    )
    assert Path(path).exists()
    assert Path(path).suffix == ".docx"


@pytest.mark.asyncio
async def test_render_pdf_fallback_on_bad_template(sample_resume: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.shared.config import get_settings

    monkeypatch.setattr(get_settings(), "storage_root", tmp_path)
    renderer = WeasyPrintRenderer()
    user_id = uuid4()
    path = await renderer.render_pdf(
        content_json=sample_resume,
        template="nonexistent-template",
        language="en",
        user_id=user_id,
    )
    assert Path(path).exists()


def test_ensure_user_dir_creates_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.shared.config import get_settings

    monkeypatch.setattr(get_settings(), "storage_root", tmp_path)
    user_id = uuid4()
    d = _ensure_user_dir(user_id)
    assert d.exists()
    assert d.name == str(user_id)
