"""Applications aggregate read API (F): /api/v1/applications.

The FE Kanban still uses /jobs (which now dual-writes the typed aggregate); this
exposes the typed pipeline + parsed JD requirements for new clients and the
future Kanban cutover. Reads only — writes still flow through the jobs router.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from src.documents.infrastructure.applications_sync import list_applications
from src.documents.infrastructure.orm import JobRequirementOrm
from src.identity.interfaces.api.deps import CurrentUserId, SessionDep

router = APIRouter()


@router.get("")
async def list_apps(user_id: CurrentUserId, session: SessionDep) -> dict[str, Any]:
    """The typed application pipeline, plus a stage->rows grouping for Kanban."""
    items = await list_applications(session, UUID(user_id))
    by_stage: dict[str, list[dict[str, Any]]] = {}
    for a in items:
        by_stage.setdefault(a["stage"], []).append(a)
    return {"items": items, "by_stage": by_stage}


@router.get("/{job_id}/requirements")
async def job_requirements(
    job_id: str, user_id: CurrentUserId, session: SessionDep
) -> list[dict[str, Any]]:
    """Parsed JD requirements (must_have | nice_to_have | ats_keyword) for a job."""
    rows = (
        (
            await session.execute(
                select(JobRequirementOrm)
                .where(JobRequirementOrm.user_id == UUID(user_id))
                .where(JobRequirementOrm.job_id == UUID(job_id))
                .order_by(JobRequirementOrm.kind, JobRequirementOrm.label)
            )
        )
        .scalars()
        .all()
    )
    return [{"id": str(r.id), "kind": r.kind, "label": r.label} for r in rows]
