"""Unit tests for documents domain entities (pure, no DB)."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from src.documents.domain.entities import Document, DocumentGenerated, Job


class TestDocument:
    def test_create(self):
        uid = uuid4()
        now = datetime.now(UTC)
        d = Document.create(
            user_id=uid,
            kind="cv",
            template="ats-classic",
            language="es",
            tone="professional",
            length="1-page",
            job_id=None,
            generated_from={"version": "1"},
            content_json={"name": "Alice"},
            now=now,
        )
        assert d.kind == "cv"
        assert d.user_id == uid
        assert d.pdf_path is None
        assert d.docx_path is None

    def test_event_emitted(self):
        uid = uuid4()
        d = Document.create(
            user_id=uid,
            kind="cv",
            template="t",
            language="es",
            tone=None,
            length=None,
            job_id=None,
            generated_from={},
            content_json={},
            now=datetime.now(UTC),
        )
        events = d.pop_events()
        assert len(events) == 1
        assert isinstance(events[0], DocumentGenerated)
        assert events[0].user_id == uid

    def test_attach_renders(self):
        d = Document.create(
            user_id=uuid4(),
            kind="cv",
            template="t",
            language="es",
            tone=None,
            length=None,
            job_id=None,
            generated_from={},
            content_json={},
            now=datetime.now(UTC),
        )
        d.attach_renders(pdf_path="/a.pdf", docx_path="/a.docx")
        assert d.pdf_path == "/a.pdf"
        assert d.docx_path == "/a.docx"

    def test_pop_events_clears(self):
        d = Document.create(
            user_id=uuid4(),
            kind="cv",
            template="t",
            language="es",
            tone=None,
            length=None,
            job_id=None,
            generated_from={},
            content_json={},
            now=datetime.now(UTC),
        )
        assert len(d.pop_events()) == 1
        assert len(d.pop_events()) == 0


class TestJob:
    def test_create_minimal(self):
        uid = uuid4()
        now = datetime.now(UTC)
        j = Job.create(user_id=uid, description_raw="Looking for a dev", now=now)
        assert j.user_id == uid
        assert j.description_parsed == {}
        assert j.embedding is None

    def test_create_full(self):
        uid = uuid4()
        now = datetime.now(UTC)
        j = Job.create(
            user_id=uid,
            description_raw="JD",
            company_name="Acme",
            title="Dev",
            url="http://jobs.acme/1",
            description_parsed={"must_haves": ["py"]},
            ats_detected="greenhouse",
            now=now,
        )
        assert j.company_name == "Acme"
        assert j.ats_detected == "greenhouse"
        assert j.description_parsed["must_haves"] == ["py"]
