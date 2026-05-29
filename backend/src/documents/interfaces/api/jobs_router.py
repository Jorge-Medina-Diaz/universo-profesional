"""Jobs tracker API: /api/v1/jobs/*

Jobs were originally a side-effect of generating CVs (one row per JD parsed).
This router exposes them as a first-class tracker: list, create, patch status,
delete. The tracker metadata (status/notes/applied_at) lives in
`description_parsed._tracker` to avoid a schema migration — the JSONB column
already exists.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from src.documents.domain.entities import Job
from src.documents.infrastructure.orm import JobOrm
from src.identity.interfaces.api.deps import CurrentUserId, SessionDep

router = APIRouter()


VALID_STATUSES = {"interested", "applied", "interviewing", "offer", "rejected", "archived"}


class JobCreate(BaseModel):
    url: str | None = None
    title: str | None = None
    company_name: str | None = None
    description_raw: str = Field(default="", max_length=20000)
    status: str = Field(default="interested")


class JobPatch(BaseModel):
    status: str | None = None
    notes: str | None = None
    applied_at: str | None = None
    # ISO date/datetime for a follow-up; "" clears it. Setting it creates a
    # job_followup reminder so the tracker drives the reminders engine.
    next_action_at: str | None = None
    title: str | None = None
    company_name: str | None = None
    url: str | None = None
    position: float | None = None


# Statuses past which a follow-up reminder no longer makes sense.
_TERMINAL_STATUSES = {"rejected", "archived", "offer"}


class JobReorder(BaseModel):
    """Reorder one or many jobs at once (Kanban DnD)."""

    items: list[dict[str, Any]] = Field(default_factory=list)


def _to_dict(row: JobOrm) -> dict[str, Any]:
    parsed = dict(row.description_parsed or {})
    tracker = dict(parsed.pop("_tracker", {}) or {})
    return {
        "id": str(row.id),
        "company_name": row.company_name,
        "title": row.title,
        "url": row.url,
        "description_raw": row.description_raw,
        "description_parsed": parsed,
        "ats_detected": row.ats_detected,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "status": tracker.get("status", "interested"),
        "notes": tracker.get("notes"),
        "applied_at": tracker.get("applied_at"),
        "next_action_at": tracker.get("next_action_at"),
        "match_score": tracker.get("match_score"),
        # Full per-dimension breakdown (dimensions/strengths/gaps/keyword_coverage)
        # cached alongside the headline score so the Kanban scorecard can render
        # without re-running the match.
        "match": tracker.get("match"),
        "position": tracker.get("position"),
    }


@router.get("")
async def list_jobs(
    user_id: CurrentUserId,
    session: SessionDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    stmt = (
        select(JobOrm)
        .where(JobOrm.user_id == UUID(user_id))
        .order_by(desc(JobOrm.created_at))
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    items = [_to_dict(r) for r in rows]
    if status_filter:
        items = [j for j in items if j["status"] == status_filter]
    # Stable sort: SQL already returned created_at DESC. We bring positioned
    # jobs to the top (sorted by their position asc) and let the rest fall
    # through in created_at-desc order.
    items.sort(
        key=lambda j: (
            0 if j.get("position") is not None else 1,
            float(j["position"]) if j.get("position") is not None else 0.0,
        )
    )
    return items


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_job(
    body: JobCreate,
    user_id: CurrentUserId,
    session: SessionDep,
) -> dict[str, Any]:
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="invalid_status")
    job = Job.create(
        user_id=UUID(user_id),
        description_raw=body.description_raw,
        company_name=body.company_name,
        title=body.title,
        url=body.url,
        description_parsed={"_tracker": {"status": body.status}},
        now=datetime.now(UTC),
    )
    row = JobOrm(
        id=job.id,
        user_id=job.user_id,
        company_name=job.company_name,
        title=job.title,
        url=job.url,
        description_raw=job.description_raw,
        description_parsed=job.description_parsed,
        ats_detected=None,
        embedding=None,
        created_at=job.created_at,
    )
    session.add(row)
    await session.commit()
    return _to_dict(row)


@router.patch("/{job_id}")
async def patch_job(
    job_id: str,
    body: JobPatch,
    user_id: CurrentUserId,
    session: SessionDep,
) -> dict[str, Any]:
    row = await session.get(JobOrm, UUID(job_id))
    if row is None or str(row.user_id) != user_id:
        raise HTTPException(status_code=404, detail="not_found")
    if body.status is not None and body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="invalid_status")
    parsed = dict(row.description_parsed or {})
    tracker = dict(parsed.get("_tracker", {}) or {})
    if body.status is not None:
        tracker["status"] = body.status
        if body.status == "applied" and not tracker.get("applied_at"):
            tracker["applied_at"] = datetime.now(UTC).isoformat()
    if body.notes is not None:
        tracker["notes"] = body.notes
    if body.applied_at is not None:
        tracker["applied_at"] = body.applied_at
    if body.next_action_at is not None:
        tracker["next_action_at"] = body.next_action_at or None
    if body.position is not None:
        tracker["position"] = float(body.position)
    parsed["_tracker"] = tracker
    row.description_parsed = parsed
    if body.title is not None:
        row.title = body.title
    if body.company_name is not None:
        row.company_name = body.company_name
    if body.url is not None:
        row.url = body.url

    # Keep the follow-up reminder in sync whenever the date or status changed.
    if body.next_action_at is not None or body.status is not None:
        await _sync_job_followup_reminder(session, row, tracker)

    await session.commit()
    return _to_dict(row)


async def _sync_job_followup_reminder(
    session: Any, row: JobOrm, tracker: dict[str, Any]
) -> None:
    """Upsert/dismiss a `job_followup` reminder from the job's next_action_at.

    Wires the application tracker into the reminders engine: a follow-up date
    becomes a due reminder (surfaced in the bell + RemindersPage + the daily
    digest email); clearing it or moving the job to a terminal status dismisses
    the reminder. Best-effort — never blocks the job update.
    """
    from datetime import datetime

    from sqlalchemy import select

    from src.shared.security import utc_now
    from src.universe.application.ports.orm import ReminderOrm

    next_action = tracker.get("next_action_at")
    status = tracker.get("status", "interested")
    title = row.title or row.company_name or "tu oferta"

    existing = (
        await session.execute(
            select(ReminderOrm)
            .where(ReminderOrm.user_id == row.user_id)
            .where(ReminderOrm.kind == "job_followup")
            .where(ReminderOrm.subject_id == row.id)
            .where(ReminderOrm.dismissed_at.is_(None))
        )
    ).scalar_one_or_none()

    # No active follow-up wanted → dismiss any open reminder.
    if not next_action or status in _TERMINAL_STATUSES:
        if existing is not None:
            existing.dismissed_at = utc_now()
        return

    try:
        due_at = datetime.fromisoformat(str(next_action).replace("Z", "+00:00"))
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=UTC)
    except ValueError:
        return  # malformed date — leave reminders untouched

    body_text = f"Haz seguimiento de «{title}»."
    if existing is not None:
        existing.due_at = due_at
        existing.title = f"Seguimiento: {title}"
        existing.body = body_text
        existing.dispatched_at = None  # re-arm the digest for the new date
    else:
        from uuid import uuid4

        session.add(
            ReminderOrm(
                id=uuid4(),
                user_id=row.user_id,
                kind="job_followup",
                subject_type="job",
                subject_id=row.id,
                title=f"Seguimiento: {title}",
                body=body_text,
                due_at=due_at,
                payload={"job_id": str(row.id)},
                created_at=utc_now(),
            )
        )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    user_id: CurrentUserId,
    session: SessionDep,
) -> None:
    row = await session.get(JobOrm, UUID(job_id))
    if row is None or str(row.user_id) != user_id:
        return
    await session.delete(row)
    await session.commit()


@router.post("/reorder")
async def reorder_jobs(
    body: JobReorder,
    user_id: CurrentUserId,
    session: SessionDep,
) -> dict[str, int]:
    """Bulk-update positions for several jobs at once.

    Body: `{ items: [ { id, position, status? }, ... ] }`. Only the listed
    jobs are touched; positions are floats so the client can insert between
    two cards without renumbering everything.
    """
    updated = 0
    for item in body.items:
        job_id = item.get("id")
        if not job_id:
            continue
        try:
            row = await session.get(JobOrm, UUID(str(job_id)))
        except ValueError:
            continue
        if row is None or str(row.user_id) != user_id:
            continue
        parsed = dict(row.description_parsed or {})
        tracker = dict(parsed.get("_tracker", {}) or {})
        if "position" in item and item["position"] is not None:
            tracker["position"] = float(item["position"])
        new_status = item.get("status")
        if new_status:
            if new_status not in VALID_STATUSES:
                raise HTTPException(status_code=400, detail="invalid_status")
            tracker["status"] = new_status
            if new_status == "applied" and not tracker.get("applied_at"):
                tracker["applied_at"] = datetime.now(UTC).isoformat()
        parsed["_tracker"] = tracker
        row.description_parsed = parsed
        updated += 1
    if updated:
        await session.commit()
    return {"updated": updated}


@router.post("/{job_id}/score")
async def compute_score(
    job_id: str,
    user_id: CurrentUserId,
    session: SessionDep,
) -> dict[str, Any]:
    """Compute the match score against the user's universe and cache it.

    Reuses the same heuristic as the `match_job_to_profile` MCP tool (embed the
    JD, retrieve top entities, average similarity) and then derives a grounded
    per-dimension breakdown (skills / experience / education) plus the keyword
    gaps and strengths via the shared `compute_match_breakdown` helper.
    """
    row = await session.get(JobOrm, UUID(job_id))
    if row is None or str(row.user_id) != user_id:
        raise HTTPException(status_code=404, detail="not_found")
    if not row.description_raw:
        raise HTTPException(status_code=400, detail="missing_description")

    from src.documents.application.match_scoring import compute_match_breakdown
    from src.documents.infrastructure.job_parser import MockJobParser
    from src.shared.embeddings import get_embeddings_service
    from src.universe.infrastructure.repositories import SqlAlchemySkillRepository
    from src.universe.infrastructure.semantic_search import PgVectorSemanticSearch

    embedder = get_embeddings_service()
    search = PgVectorSemanticSearch(session)
    vec = await embedder.embed(row.description_raw)
    retrieved = await search.search(user_id=row.user_id, embedding=vec, top_k=20)

    # ATS keywords: prefer the keywords parsed at ingestion, else parse now.
    parsed = dict(row.description_parsed or {})
    needed_keywords = parsed.get("ats_keywords")
    if not needed_keywords:
        jd = await MockJobParser().parse(url=row.url, description=row.description_raw)
        needed_keywords = jd.get("ats_keywords", [])
    your_skills = [s.name for s in await SqlAlchemySkillRepository(session).list(row.user_id)]

    breakdown = compute_match_breakdown(
        retrieved=retrieved,
        needed_keywords=list(needed_keywords or []),
        your_skills=your_skills,
    )

    tracker = dict(parsed.get("_tracker", {}) or {})
    tracker["match_score"] = breakdown["match_score"]
    tracker["match"] = breakdown
    parsed["_tracker"] = tracker
    row.description_parsed = parsed
    await session.commit()
    return _to_dict(row)


@router.get("/{job_id}/documents")
async def job_documents(
    job_id: str,
    user_id: CurrentUserId,
    session: SessionDep,
) -> list[dict[str, Any]]:
    """Documents (CVs/cover letters) generated for this job — links the tracker
    to the artifacts produced for each application."""
    from src.documents.infrastructure.orm import DocumentOrm

    rows = (
        await session.execute(
            select(DocumentOrm)
            .where(DocumentOrm.user_id == UUID(user_id))
            .where(DocumentOrm.job_id == UUID(job_id))
            .order_by(desc(DocumentOrm.created_at))
        )
    ).scalars().all()
    return [
        {
            "id": str(d.id),
            "kind": d.kind,
            "template": d.template,
            "language": d.language,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "has_pdf": bool(d.pdf_path),
        }
        for d in rows
    ]
