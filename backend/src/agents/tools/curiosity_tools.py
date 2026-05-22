"""Server-side tools for the curiosity_specialist.

Three helpers:
  - `get_domain_template`: look up the curated deep-dive template for a domain.
  - `add_learning_note`: write a structured learning journal (delegates to
     the notes use-case but persists `source_metadata` JSONB so we keep the
     raw stack/modules/depth payload).
  - `schedule_learning_followup`: drop a Reminder with kind="learning_followup"
     so the coordinator can resurface the topic in ~10 days.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from agno.run.base import RunContext
from agno.tools import tool
from sqlalchemy import select

from src.agents.domain_templates import (
    fallback_template,
    get_template_for,
)
from src.notes.application.use_cases import CreateNote, UpdateNote
from src.notes.infrastructure.repositories import SqlAlchemyNoteRepository
from src.shared.db import get_session_factory, set_rls_user
from src.shared.security import utc_now
from src.shared.uow import UnitOfWork
from src.universe.infrastructure.orm import ReminderOrm
from src.universe.infrastructure.scheduler import ArqEmbeddingScheduler

# Cap to avoid spamming reminders if the user explores many domains.
MAX_OPEN_LEARNING_REMINDERS = 3
FOLLOWUP_DELAY_DAYS = 10


@tool(
    name="get_domain_template",
    description=(
        "Return the curated deep-dive template for a domain (sections, chip "
        "options, etc.). Returns the curated template if `domain` matches one "
        "of the 8 supported domains (ecommerce, ai_ml, mobile, devops, "
        "cybersec, design_systems, data_eng, web3), and a generic fallback "
        "template otherwise. Always returns a template — never None. The "
        "result is shaped like `{title, intro, sections, is_fallback}` ready "
        "to feed into `present_deep_dive`."
    ),
)
def get_domain_template(domain: str) -> dict[str, Any]:
    curated = get_template_for(domain)
    if curated is not None:
        return {**curated, "is_fallback": False}
    return {**fallback_template(domain), "is_fallback": True}


@tool(
    name="add_learning_note",
    description=(
        "Create or update a learning-journal note for a domain the user is "
        "exploring. If a `note_id` is passed, the existing note's body is "
        "extended (with a dated separator). Otherwise a new note is created. "
        "Always pass `tags` including 'learning' and the domain slug. "
        "`source_metadata` should hold the raw structured payload "
        "{topic, domain, sections} returned by `present_deep_dive` for later "
        "structured queries."
    ),
)
async def add_learning_note(
    run_context: RunContext,
    body_md: str,
    tags: list[str],
    source_metadata: dict[str, Any],
    title: str | None = None,
    note_id: str | None = None,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, UUID(user_id))
        repo = SqlAlchemyNoteRepository(session)
        scheduler = ArqEmbeddingScheduler()
        uow = UnitOfWork(session)
        if note_id:
            existing = await repo.get(UUID(user_id), UUID(note_id))
            if existing is None:
                return {"ok": False, "error": "note not found"}
            existing_body = (existing.body_md or "").rstrip()
            new_body = f"{existing_body}\n\n---\n\n[{utc_now().date().isoformat()}] update:\n{body_md.strip()}"
            merged_tags = sorted({*(existing.tags or []), *(t.lower().strip() for t in tags if t.strip())})
            merged_meta = {**(existing.source_metadata or {}), **(source_metadata or {})}
            uc = UpdateNote(repo, scheduler)
            result = await uc.execute(
                user_id=user_id,
                note_id=note_id,
                patch={
                    "body_md": new_body,
                    "tags": merged_tags,
                    "source_metadata": merged_meta,
                },
                uow=uow,
            )
        else:
            uc = CreateNote(repo, scheduler)
            result = await uc.execute(
                user_id=user_id,
                payload={
                    "body_md": body_md,
                    "title": title,
                    "tags": [t.lower().strip() for t in tags if t.strip()],
                    "source_metadata": source_metadata or {},
                },
                uow=uow,
            )
        if result.is_failure:
            await uow.rollback()
            return {"ok": False, "error": str(result.error)}
        await uow.commit()
        return {"ok": True, "note": result.value}


@tool(
    name="schedule_learning_followup",
    description=(
        "Schedule a soft follow-up reminder ~10 days from now so the coordinator "
        "can resurface a learning topic on a future session ('hace 10 días "
        "empezaste a explorar X, ¿cómo va?'). Idempotent per domain: if there "
        "is already an open follow-up for the same domain, this is a no-op. "
        "Capped at 3 open learning follow-ups per user to avoid spam."
    ),
)
async def schedule_learning_followup(
    run_context: RunContext,
    domain: str,
    note_id: str | None = None,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    domain_slug = domain.strip().lower()
    if not domain_slug:
        return {"ok": False, "error": "missing domain"}
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, UUID(user_id))
        existing_open = (
            await session.execute(
                select(ReminderOrm)
                .where(ReminderOrm.user_id == UUID(user_id))
                .where(ReminderOrm.kind == "learning_followup")
                .where(ReminderOrm.dismissed_at.is_(None))
            )
        ).scalars().all()
        # Idempotent per domain.
        for r in existing_open:
            if (r.payload or {}).get("domain") == domain_slug:
                return {"ok": True, "skipped": "already_scheduled", "reminder_id": str(r.id)}
        # Cap on total open learning reminders.
        if len(existing_open) >= MAX_OPEN_LEARNING_REMINDERS:
            return {"ok": True, "skipped": "cap_reached"}
        now = utc_now()
        rid = uuid4()
        session.add(
            ReminderOrm(
                id=rid,
                user_id=UUID(user_id),
                kind="learning_followup",
                subject_type="note",
                subject_id=UUID(note_id) if note_id else None,
                title=f"¿Cómo va lo de {domain_slug}?",
                body=(
                    f"Hace ~{FOLLOWUP_DELAY_DAYS} días empezaste a explorar **{domain_slug}**. "
                    f"¿Has profundizado, cambiado de foco o lo aparcaste?"
                ),
                due_at=now + timedelta(days=FOLLOWUP_DELAY_DAYS),
                payload={"domain": domain_slug, "note_id": note_id},
                created_at=now,
            )
        )
        await session.commit()
        return {"ok": True, "reminder_id": str(rid)}
