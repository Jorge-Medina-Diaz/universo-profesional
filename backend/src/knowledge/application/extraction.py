"""Coherence half of the knowledge store: document text → universe entities.

After a document is ingested as a raw substrate, this pulls the clear
technical signals out of it and routes them through the SAME coherence
engine the agent uses, so the graph (source of truth) absorbs what's in the
document and dedups/merges it like any other write. The raw text stays in
the substrate, re-processable.

Conservative by design: we only extract skills/topics (the highest-signal,
lowest-noise entity for an arbitrary paper/PDF). Mock LLM mode is a no-op.
"""
from __future__ import annotations

from uuid import UUID

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.shared.config import get_settings
from src.shared.db import get_session_factory, set_rls_user

logger = structlog.get_logger(__name__)

_MAX_DOC_CHARS = 12_000
_MAX_SKILLS = 15

_SYSTEM = (
    "You read a professional document (paper, PDF, notes) and extract: "
    "(1) the technical skills/technologies/methodologies it demonstrates or "
    "discusses — conservative, only clear professionally-relevant items, no "
    "generic words; category in [hard, soft, tool, methodology], level "
    "(optional) in [basic, intermediate, high, expert]. "
    "(2) a 2-3 sentence `summary` of what the document is about, in the "
    "document's language. "
    "(3) up to 6 short `topics` (single words / short phrases) for tagging."
)


class _ExtractedSkill(BaseModel):
    name: str
    category: str = "hard"
    level: str | None = None


class _Extraction(BaseModel):
    skills: list[_ExtractedSkill] = Field(default_factory=list)
    summary: str = ""
    topics: list[str] = Field(default_factory=list)


async def _load_document(user_id: UUID, document_id: UUID) -> tuple[str, str]:
    """Return (title, concatenated_text) for a knowledge document."""
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, user_id)
        title_row = (
            await session.execute(
                text("SELECT title FROM knowledge_documents WHERE id = :did"),
                {"did": str(document_id)},
            )
        ).first()
        rows = (
            await session.execute(
                text(
                    """
                    SELECT content FROM knowledge_chunks
                    WHERE document_id = :did
                    ORDER BY chunk_index ASC
                    """
                ),
                {"did": str(document_id)},
            )
        ).all()
    title = title_row.title if title_row else "documento"
    body = "\n\n".join(r.content for r in rows)[:_MAX_DOC_CHARS]
    return title, body


async def _create_summary_note(
    user_id: UUID, document_id: UUID, *, title: str, summary: str, topics: list[str]
) -> None:
    """Persist the LLM summary as a narrative Note (memory layer 2)."""
    from src.notes.application.use_cases import CreateNote
    from src.notes.infrastructure.repositories import SqlAlchemyNoteRepository
    from src.shared.uow import unit_of_work
    from src.universe.infrastructure.scheduler import ArqEmbeddingScheduler

    tags = ["knowledge"] + [t.strip().lower() for t in topics if t.strip()][:6]
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, user_id)
        uc = CreateNote(SqlAlchemyNoteRepository(session), ArqEmbeddingScheduler())
        async with unit_of_work(session) as uow:
            await uc.execute(
                user_id=str(user_id),
                payload={
                    "body_md": summary,
                    "title": f"Resumen: {title}"[:200],
                    "tags": tags,
                    "source": "knowledge_extraction",
                    "source_metadata": {"document_id": str(document_id)},
                },
                uow=uow,
            )
            await uow.commit()


async def _mark_status(user_id: UUID, document_id: UUID, status: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, user_id)
        await session.execute(
            text(
                "UPDATE knowledge_documents SET status = :s, updated_at = now() "
                "WHERE id = :did"
            ),
            {"s": status, "did": str(document_id)},
        )
        await session.commit()


async def run_extraction(user_id: str, document_id: str) -> dict[str, int]:
    """Extract skills from a knowledge document and route them through the
    coherence engine. Returns a small summary. Never raises — it's a
    best-effort background pass."""
    uid = UUID(user_id)
    did = UUID(document_id)
    settings = get_settings()

    if settings.llm_provider_resolved == "mock":
        # No real LLM → can't extract meaningfully. Leave the substrate in
        # place; the agent can still recall it via search_knowledge.
        await _mark_status(uid, did, "ingested")
        return {"skills_upserted": 0, "note_created": 0}

    title, body = await _load_document(uid, did)
    if not body.strip():
        await _mark_status(uid, did, "ingested")
        return {"skills_upserted": 0, "note_created": 0}

    from src.shared.llm_client import get_llm_client

    try:
        extraction = await get_llm_client().structured(
            system=_SYSTEM,
            prompt=f"Read this document and extract its signals:\n\n{body}",
            schema=_Extraction,
            max_tokens=1536,
            temperature=0.0,
        )
    except Exception as exc:
        logger.warning("knowledge_extraction_llm_failed", document_id=document_id, error=str(exc))
        await _mark_status(uid, did, "ingested")
        return {"skills_upserted": 0, "note_created": 0}

    # Narrative layer (memory layer 2): persist the summary as a Note.
    note_created = False
    summary = (extraction.summary or "").strip()
    if summary:
        try:
            await _create_summary_note(
                uid, did, title=title, summary=summary, topics=extraction.topics or []
            )
            note_created = True
        except Exception as exc:
            logger.warning(
                "knowledge_summary_note_failed", document_id=document_id, error=str(exc)
            )

    skills = (extraction.skills or [])[:_MAX_SKILLS]
    if not skills:
        await _mark_status(uid, did, "extracted")
        return {"skills_upserted": 0, "note_created": int(note_created)}

    from src.coherence.application.upsert_use_cases import UpsertUniverseEntity
    from src.coherence.infrastructure.change_log_repo import (
        SqlAlchemyChangeLogRepository,
    )
    from src.coherence.infrastructure.semantic_matcher import PgVectorSemanticMatcher
    from src.shared.uow import unit_of_work

    upserted = 0
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, uid)
        uc = UpsertUniverseEntity(
            session,
            change_log=SqlAlchemyChangeLogRepository(session),
            semantic_matcher=PgVectorSemanticMatcher(session),
        )
        for skill in skills:
            payload = {"name": skill.name, "category": skill.category}
            if skill.level:
                payload["level"] = skill.level
            try:
                async with unit_of_work(session) as uow:
                    await uc.execute(
                        entity_type="skill",
                        user_id=str(uid),
                        payload=payload,
                        uow=uow,
                        source="knowledge_extraction",
                    )
                    await uow.commit()
                upserted += 1
            except Exception as exc:
                logger.warning(
                    "knowledge_skill_upsert_failed",
                    document_id=document_id,
                    skill=skill.name,
                    error=str(exc),
                )

    await _mark_status(uid, did, "extracted")
    logger.info(
        "knowledge_extracted",
        user_id=user_id,
        document_id=document_id,
        skills_upserted=upserted,
        note_created=note_created,
    )
    return {"skills_upserted": upserted, "note_created": int(note_created)}
