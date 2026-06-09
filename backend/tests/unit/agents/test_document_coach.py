"""Unit tests for document_coach (P1.D merge) and document tools."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from agno.run.base import RunContext
from src.agents.tools.document_tools import (
    _TEMPLATE_META,
    get_document,
    get_document_template,
    list_document_templates,
)


def _make_run_context(user_id: str | None) -> RunContext:
    return RunContext(
        run_id=str(uuid4()),
        session_id=str(uuid4()),
        user_id=user_id,
    )


def make_mock_document(**overrides) -> MagicMock:
    """Return a pre-configured MagicMock for a DocumentOrm row.

    Defaults represent a typical CV document. Override any attribute via
    keyword arguments (e.g. kind="cover_letter", content_json={...}).
    """
    mock = MagicMock()
    mock.id = uuid4()
    mock.kind = "cv"
    mock.template = "modern"
    mock.language = "es"
    mock.tone = "professional"
    mock.length = "1-page"
    mock.pdf_path = "./test.pdf"
    mock.docx_path = None
    mock.share_token = None
    mock.job_id = None
    mock.created_at = MagicMock()
    mock.created_at.isoformat.return_value = "2026-01-01T00:00:00+00:00"
    mock.content_json = {
        "basics": {
            "name": "Ada Lovelace",
            "label": "Senior Developer",
            "summary": "Passionate developer...",
        },
        "work": [
            {"position": "Dev", "name": "Acme", "startDate": "2020-01", "endDate": None}
        ],
        "skills": [{"name": "Python"}, {"name": "React"}],
    }
    for key, value in overrides.items():
        setattr(mock, key, value)
    return mock


class TestListDocumentTemplates:
    def test_returns_all_templates(self):
        result = list_document_templates.entrypoint()
        assert result["count"] == len(_TEMPLATE_META)
        assert len(result["templates"]) == len(_TEMPLATE_META)
        names = {t["name"] for t in result["templates"]}
        assert names == {"ats-classic", "modern", "minimal", "cover-letter-classic"}

    def test_each_template_has_required_fields(self):
        result = list_document_templates.entrypoint()
        for t in result["templates"]:
            assert "name" in t
            assert "kind" in t
            assert "description" in t
            assert "best_for" in t
            assert "language_support" in t


class TestGetDocumentTemplate:
    def test_returns_known_template(self):
        result = get_document_template.entrypoint("modern")
        assert result["name"] == "modern"
        assert result["kind"] == "cv"
        assert "tech" in result["best_for"]

    def test_returns_error_for_unknown_template(self):
        result = get_document_template.entrypoint("nonexistent")
        assert "error" in result
        assert "available" in result

    def test_discovers_uncatalogued_file(self, tmp_path):
        # Simulate a template file that exists but isn't in _TEMPLATE_META
        with patch(
            "src.agents.tools.document_tools._TEMPLATE_DIR", tmp_path
        ):
            (tmp_path / "new-template.html.j2").write_text("<html></html>")
            result = get_document_template.entrypoint("new-template")
            assert result["name"] == "new-template"
            assert result["kind"] == "cv"
            assert "pendiente" in result["description"].lower()


class TestGetDocument:
    async def test_get_document_found(self):
        run_context = _make_run_context(str(uuid4()))

        mock_doc = make_mock_document()

        mock_session = AsyncMock()
        mock_execute = MagicMock()
        mock_execute.scalar_one_or_none.return_value = mock_doc
        mock_session.execute.return_value = mock_execute

        with patch(
            "src.agents.tools.document_tools.with_user_session"
        ) as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_document.entrypoint(run_context, str(mock_doc.id))

        assert result["id"] == str(mock_doc.id)
        assert result["kind"] == "cv"
        assert result["template"] == "modern"
        assert result["tone"] == "professional"
        assert result["has_pdf"] is True
        assert result["has_docx"] is False
        assert result["summary"]["name"] == "Ada Lovelace"
        assert result["summary"]["label"] == "Senior Developer"
        assert result["summary"]["experience_count"] == 1
        assert result["summary"]["skill_count"] == 2

    async def test_get_document_not_found(self):
        run_context = _make_run_context(str(uuid4()))

        mock_session = AsyncMock()
        mock_execute = MagicMock()
        mock_execute.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_execute

        with patch(
            "src.agents.tools.document_tools.with_user_session"
        ) as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_document.entrypoint(run_context, str(uuid4()))

        assert "error" in result
        assert result["error"] == "Document not found"

    async def test_get_document_missing_user_id(self):
        run_context = _make_run_context(None)

        result = await get_document.entrypoint(run_context, str(uuid4()))
        assert result["error"] == "missing user_id"

    async def test_get_document_cover_letter_body(self):
        run_context = _make_run_context(str(uuid4()))

        mock_doc = make_mock_document(
            kind="cover_letter",
            template="cover-letter-classic",
            tone="formal",
            length=None,
            pdf_path=None,
            job_id=uuid4(),
            content_json={
                "basics": {"name": "Ada Lovelace"},
                "cover_letter_body": "Estimado reclutador...",
            },
        )

        mock_session = AsyncMock()
        mock_execute = MagicMock()
        mock_execute.scalar_one_or_none.return_value = mock_doc
        mock_session.execute.return_value = mock_execute

        with patch(
            "src.agents.tools.document_tools.with_user_session"
        ) as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_document.entrypoint(run_context, str(mock_doc.id))

        assert result["kind"] == "cover_letter"
        assert result["summary"]["cover_letter_body"] == "Estimado reclutador..."
        assert result["job_id"] == str(mock_doc.job_id)


class TestDocumentCoachBuild:
    def test_builds_with_correct_tools(self):
        from src.agents.specialists.document_coach import build_document_coach

        mock_db = MagicMock()
        specialist = build_document_coach(db=mock_db)

        assert specialist.name == "document_coach"
        tool_names = {t.name for t in specialist.tools}
        assert "get_universe_summary" in tool_names
        assert "list_documents" in tool_names
        assert "get_document" in tool_names
        assert "list_document_templates" in tool_names
        assert "get_document_template" in tool_names
        assert "present_document_preview" in tool_names
        assert "propose_document_generation" in tool_names
        assert "propose_cover_letter" in tool_names
        assert "propose_cv_regenerate" in tool_names

    def test_instructions_contain_discovery_flow(self):
        from src.agents.specialists.document_coach import build_document_coach

        mock_db = MagicMock()
        specialist = build_document_coach(db=mock_db)

        instructions = "\n".join(specialist.instructions)
        assert "DIMENSIONES" in instructions
        assert "qué documento" in instructions
        assert "ocasi" in instructions
        assert "oferta concreta" in instructions
        assert "tono" in instructions
        assert "UNA pregunta" in instructions

    def test_instructions_forbid_dumping_templates(self):
        from src.agents.specialists.document_coach import build_document_coach

        mock_db = MagicMock()
        specialist = build_document_coach(db=mock_db)

        instructions = "\n".join(specialist.instructions)
        assert "NUNCA listes todas de golpe" in instructions
        assert "NUNCA generes sin" in instructions
        assert "inventes una oferta" in instructions

    def test_instructions_contain_generation_gate(self):
        from src.agents.specialists.document_coach import build_document_coach

        mock_db = MagicMock()
        specialist = build_document_coach(db=mock_db)

        instructions = "\n".join(specialist.instructions)
        assert "GENERACI" in instructions
        assert "propose_document_generation" in instructions
        assert "propose_cover_letter" in instructions
        assert "propose_cv_regenerate" in instructions

    def test_instructions_contain_post_generation(self):
        from src.agents.specialists.document_coach import build_document_coach

        mock_db = MagicMock()
        specialist = build_document_coach(db=mock_db)

        instructions = "\n".join(specialist.instructions)
        assert "TRAS GENERAR" in instructions
        assert "REGLA DE ORO" in instructions
