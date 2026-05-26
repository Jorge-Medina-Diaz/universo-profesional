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
    title: str | None = None
    company_name: str | None = None
    url: str | None = None
    position: float | None = None


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
        "match_score": tracker.get("match_score"),
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
    await session.commit()
    return _to_dict(row)


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
    """Compute match score against the user's universe and cache it on the job.

    Reuses the same heuristic as the `match_job_to_profile` MCP tool:
    embed the JD text, retrieve top entities, average similarity.
    """
    row = await session.get(JobOrm, UUID(job_id))
    if row is None or str(row.user_id) != user_id:
        raise HTTPException(status_code=404, detail="not_found")
    if not row.description_raw:
        raise HTTPException(status_code=400, detail="missing_description")

    from src.shared.embeddings import get_embeddings_service
    from src.universe.infrastructure.semantic_search import PgVectorSemanticSearch

    embedder = get_embeddings_service()
    search = PgVectorSemanticSearch(session)
    vec = await embedder.embed(row.description_raw)
    retrieved = await search.search(user_id=row.user_id, embedding=vec, top_k=20)
    avg = sum(r["score"] for r in retrieved) / len(retrieved) if retrieved else 0.0
    match_score = int(round(max(0.0, min(1.0, (avg + 1) / 2)) * 100))

    parsed = dict(row.description_parsed or {})
    tracker = dict(parsed.get("_tracker", {}) or {})
    tracker["match_score"] = match_score
    parsed["_tracker"] = tracker
    row.description_parsed = parsed
    await session.commit()
    return _to_dict(row)
