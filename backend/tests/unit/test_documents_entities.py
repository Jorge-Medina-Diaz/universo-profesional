"""Unit tests for documents domain entities."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from src.documents.domain.entities import Document, DocumentGenerated, Job


class TestDocument:
    def test_create_emits_event(self):
        now = datetime.now(UTC)
        doc = Document.create(
            user_id=uuid4(),
            kind="cv",
            template="modern",
            language="es",
            tone="professional",
            length="1-page",
            job_id=None,
            generated_from={},
            content_json={},
            now=now,
        )
        assert doc.kind == "cv"
        events = doc.pop_events()
        assert len(events) == 1
        assert isinstance(events[0], DocumentGenerated)

    def test_attach_renders(self):
        now = datetime.now(UTC)
        doc = Document.create(
            user_id=uuid4(),
            kind="cv",
            template="modern",
            language="es",
            tone="professional",
            length="1-page",
            job_id=None,
            generated_from={},
            content_json={},
            now=now,
        )
        doc.attach_renders(pdf_path="/tmp/x.pdf", docx_path="/tmp/x.docx")
        assert doc.pdf_path == "/tmp/x.pdf"
        assert doc.docx_path == "/tmp/x.docx"

    def test_make_share_token(self):
        now = datetime.now(UTC)
        doc = Document.create(
            user_id=uuid4(),
            kind="cv",
            template="modern",
            language="es",
            tone="professional",
            length="1-page",
            job_id=None,
            generated_from={},
            content_json={},
            now=now,
        )
        doc.make_share_token(token="abc", expires_at=now)
        assert doc.share_token == "abc"


class TestJob:
    def test_create(self):
        now = datetime.now(UTC)
        job = Job.create(
            user_id=uuid4(),
            description_raw="Build things",
            company_name="Acme",
            title="Dev",
            now=now,
        )
        assert job.company_name == "Acme"
        assert job.description_parsed == {}
