"""Goals REST API — /api/v1/goals/*

Thin CRUD. The schema is small enough that we avoid a separate domain/use
case layer and let the router compose SQL directly via the same `GoalOrm`
the agent tools use (`agents/tools/goals_tools.py`).
"""
from __future__ import annotations

from datetime import date as _date
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.shared.security import utc_now
from src.universe.infrastructure.orm import GoalOrm

router = APIRouter()

VALID_HORIZONS = {"3_months", "6_months", "1_year", "long_term"}
VALID_STATUS = {"active", "paused", "completed", "dropped"}


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    horizon: str
    description: str | None = None
    target_date: str | None = None
    subtasks: list[str] = Field(default_factory=list)


class GoalPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    target_date: str | None = None
    status: str | None = None
    subtasks: list[str] | None = None


def _serialize(g: GoalOrm) -> dict[str, Any]:
    return {
        "id": str(g.id),
        "horizon": g.horizon,
        "title": g.title,
        "description": g.description,
        "status": g.status,
        "target_date": g.target_date.isoformat() if g.target_date else None,
        "details": g.details or {},
        "created_at": g.created_at.isoformat(),
        "updated_at": g.updated_at.isoformat(),
        "completed_at": g.completed_at.isoformat() if g.completed_at else None,
    }


@router.get("")
async def list_goals(
    user_id: CurrentUserId,
    session: SessionDep,
    status: str = Query(default="active"),
    limit: int = Query(default=20, le=100),
) -> list[dict[str, Any]]:
    stmt = select(GoalOrm).where(GoalOrm.user_id == UUID(user_id))
    if status != "*":
        stmt = stmt.where(GoalOrm.status == status)
    stmt = stmt.order_by(
        GoalOrm.target_date.asc().nulls_last(),
        GoalOrm.created_at.desc(),
    ).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_serialize(g) for g in rows]


@router.post("", status_code=201)
async def create_goal(
    user_id: CurrentUserId,
    session: SessionDep,
    body: GoalCreate,
) -> dict[str, Any]:
    if body.horizon not in VALID_HORIZONS:
        raise HTTPException(status_code=400, detail=f"horizon must be one of {sorted(VALID_HORIZONS)}")
    parsed_date: _date | None = None
    if body.target_date:
        try:
            parsed_date = _date.fromisoformat(body.target_date)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="target_date must be ISO YYYY-MM-DD"
            ) from None
    details: dict[str, Any] = {}
    if body.subtasks:
        details["subtasks"] = [
            {"title": s.strip(), "done": False} for s in body.subtasks if s.strip()
        ]
    now = utc_now()
    goal = GoalOrm(
        id=uuid4(),
        user_id=UUID(user_id),
        horizon=body.horizon,
        title=body.title.strip(),
        description=(body.description or "").strip() or None,
        status="active",
        target_date=parsed_date,
        details=details or None,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    return _serialize(goal)


@router.patch("/{goal_id}")
async def patch_goal(
    user_id: CurrentUserId,
    session: SessionDep,
    goal_id: str,
    body: GoalPatch,
) -> dict[str, Any]:
    goal = (
        await session.execute(
            select(GoalOrm)
            .where(GoalOrm.id == UUID(goal_id))
            .where(GoalOrm.user_id == UUID(user_id))
        )
    ).scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=404, detail="goal not found")
    if body.title is not None:
        v = body.title.strip()
        if v:
            goal.title = v
    if body.description is not None:
        goal.description = body.description.strip() or None
    if body.target_date is not None:
        if body.target_date == "":
            goal.target_date = None
        else:
            try:
                goal.target_date = _date.fromisoformat(body.target_date)
            except ValueError:
                raise HTTPException(
                status_code=400, detail="target_date must be ISO YYYY-MM-DD"
            ) from None
    if body.status is not None:
        if body.status not in VALID_STATUS:
            raise HTTPException(status_code=400, detail=f"status must be one of {sorted(VALID_STATUS)}")
        goal.status = body.status
        goal.completed_at = utc_now() if body.status == "completed" else None
    if body.subtasks is not None:
        new_details = dict(goal.details or {})
        new_details["subtasks"] = [
            {"title": s.strip(), "done": False} for s in body.subtasks if s.strip()
        ]
        goal.details = new_details
    goal.updated_at = utc_now()
    await session.commit()
    await session.refresh(goal)
    return _serialize(goal)


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    user_id: CurrentUserId,
    session: SessionDep,
    goal_id: str,
) -> None:
    goal = (
        await session.execute(
            select(GoalOrm)
            .where(GoalOrm.id == UUID(goal_id))
            .where(GoalOrm.user_id == UUID(user_id))
        )
    ).scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=404, detail="goal not found")
    await session.delete(goal)
    await session.commit()
