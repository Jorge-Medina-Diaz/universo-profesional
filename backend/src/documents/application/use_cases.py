"""Document use cases: generate CV, list, get, share."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.documents.application.ports import (
    DocumentRepository,
    JobParser,
    JobRepository,
    LlmClient,
    Renderer,
)
from src.documents.domain.entities import Document, Job
from src.shared.embeddings import EmbeddingsProvider
from src.shared.errors import NotFoundError, ValidationError
from src.shared.result import Result, err, ok
from src.shared.security import generate_token, utc_in, utc_now
from src.shared.uow import UnitOfWork
from src.universe.application.ports import SemanticSearchPort


@dataclass(frozen=True)
class GenerateCvInput:
    job_url: str | None = None
    job_description: str | None = None
    template: str = "ats-classic"
    language: str = "es"
    tone: str = "professional"
    length: str = "1-page"
    kind: str = "cv"  # "cv" | "cover_letter"


@dataclass(frozen=True)
class GeneratedDocumentDto:
    document_id: str
    pdf_url: str | None
    docx_url: str | None
    json_resume: dict[str, Any]


class GenerateCv:
    def __init__(
        self,
        documents: DocumentRepository,
        jobs: JobRepository,
        parser: JobParser,
        embedder: EmbeddingsProvider,
        search: SemanticSearchPort,
        llm: LlmClient,
        renderer: Renderer,
    ) -> None:
        self._docs = documents
        self._jobs = jobs
        self._parser = parser
        self._embed = embedder
        self._search = search
        self._llm = llm
        self._renderer = renderer

    async def execute(
        self, *, user_id: str, payload: GenerateCvInput, uow: UnitOfWork
    ) -> Result[GeneratedDocumentDto, ValidationError]:
        if not payload.job_url and not payload.job_description:
            return err(ValidationError("Either job_url or job_description is required"))

        uid = UUID(user_id)
        now = utc_now()

        # 1) Parse JD
        parsed = await self._parser.parse(
            url=payload.job_url, description=payload.job_description
        )
        job = Job.create(
            user_id=uid,
            description_raw=payload.job_description or parsed.get("description_raw", ""),
            company_name=parsed.get("company"),
            title=parsed.get("title"),
            url=payload.job_url,
            description_parsed=parsed,
            ats_detected=parsed.get("ats"),
            now=now,
        )
        await self._jobs.add(job)

        # 2) Embed JD
        jd_text = (
            payload.job_description or parsed.get("description_raw", "")
            or " ".join(str(v) for v in parsed.values())
        )
        jd_vec = await self._embed.embed(jd_text)

        # 3) Retrieve top entities
        retrieved = await self._search.search(
            user_id=uid, embedding=jd_vec, top_k=30
        )

        # 4) LLM (mock) — produces JSON Resume (or cover-letter body for kind=cover_letter)
        if payload.kind == "cover_letter":
            content = await self._llm.generate_cover_letter(
                job_summary=parsed,
                retrieved=retrieved,
                language=payload.language,
                tone=payload.tone,
            )
        else:
            content = await self._llm.generate_cv_bullets(
                job_summary=parsed,
                retrieved=retrieved,
                language=payload.language,
                tone=payload.tone,
            )

        # 5) Persist document
        document = Document.create(
            user_id=uid,
            kind=payload.kind if payload.kind in ("cv", "cover_letter") else "cv",
            template=payload.template,
            language=payload.language,
            tone=payload.tone,
            length=payload.length,
            job_id=job.id,
            generated_from={
                "retrieved": [
                    {"entity_type": r["entity_type"], "entity_id": r["entity_id"]}
                    for r in retrieved
                ],
                "job_id": str(job.id),
            },
            content_json=content,
            now=now,
        )
        await self._docs.add(document)

        # 6) Render. Cover letters get a different template + simpler DOCX.
        render_template = (
            "cover-letter-classic" if payload.kind == "cover_letter" else payload.template
        )
        pdf_path = await self._renderer.render_pdf(
            content_json=content,
            template=render_template,
            language=payload.language,
            user_id=uid,
        )
        docx_path = await self._renderer.render_docx(
            content_json=content,
            template=render_template,
            language=payload.language,
            user_id=uid,
        )
        # Derive the render outcome from the produced PDF key (.html = the
        # WeasyPrint fallback fired → degraded; None = failed). Persisting it
        # makes a degraded/failed render visible instead of silent.
        render_status = Document.derive_render_status(pdf_path)
        await self._docs.update_renders(
            document_id=document.id,
            pdf_path=pdf_path,
            docx_path=docx_path,
            render_status=render_status,
        )
        document.attach_renders(pdf_path=pdf_path, docx_path=docx_path)

        uow.add_events(document.pop_events())

        from src.shared.config import get_settings

        base = get_settings().canonical_base_url
        return ok(
            GeneratedDocumentDto(
                document_id=str(document.id),
                pdf_url=f"{base}/api/v1/documents/{document.id}/pdf" if pdf_path else None,
                docx_url=f"{base}/api/v1/documents/{document.id}/docx" if docx_path else None,
                json_resume=content,
            )
        )


class ListDocuments:
    def __init__(self, documents: DocumentRepository) -> None:
        self._docs = documents

    async def execute(
        self, *, user_id: str, kind: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        docs = await self._docs.list(UUID(user_id), kind=kind, limit=limit)
        return [
            {
                "id": str(d.id),
                "kind": d.kind,
                "template": d.template,
                "language": d.language,
                "tone": d.tone,
                "length": d.length,
                "created_at": d.created_at.isoformat(),
                "has_pdf": d.pdf_path is not None,
                "has_docx": d.docx_path is not None,
                "render_status": getattr(d, "render_status", "ready"),
                "share_token": d.share_token,
                # Entity ids this document was generated from — lets the
                # frontend draw document→entity edges in the universe graph.
                "source_entity_ids": [
                    str(r.get("entity_id"))
                    for r in ((d.generated_from or {}).get("retrieved") or [])
                    if r.get("entity_id")
                ],
            }
            for d in docs
        ]


class GetDocument:
    def __init__(self, documents: DocumentRepository) -> None:
        self._docs = documents

    async def execute(
        self, *, user_id: str, document_id: str
    ) -> Result[dict[str, Any], NotFoundError]:
        doc = await self._docs.get(UUID(user_id), UUID(document_id))
        if doc is None:
            return err(NotFoundError("Document not found"))
        return ok(
            {
                "id": str(doc.id),
                "kind": doc.kind,
                "template": doc.template,
                "language": doc.language,
                "tone": doc.tone,
                "length": doc.length,
                "content_json": doc.content_json,
                "render_status": getattr(doc, "render_status", "ready"),
                "has_pdf": doc.pdf_path is not None,
                "has_docx": doc.docx_path is not None,
                "share_token": doc.share_token,
                "created_at": doc.created_at.isoformat(),
            }
        )


class ShareDocument:
    def __init__(self, documents: DocumentRepository) -> None:
        self._docs = documents

    async def execute(
        self, *, user_id: str, document_id: str, expires_in_days: int | None = 30
    ) -> Result[dict[str, str], NotFoundError]:
        doc = await self._docs.get(UUID(user_id), UUID(document_id))
        if doc is None:
            return err(NotFoundError("Document not found"))
        token = generate_token(24)
        expires_at = utc_in(days=expires_in_days) if expires_in_days else None
        await self._docs.set_share_token(doc.id, token, expires_at)
        from src.shared.config import get_settings

        base = get_settings().canonical_base_url
        return ok({"share_token": token, "share_url": f"{base}/share/{token}"})
