"""Tools for the `goals_specialist`.

Goals are short structured rows (id, horizon, title, target_date, status,
details JSONB). We keep them as plain SQL CRUD here — no separate
domain/use-case layer because the entity is too simple to justify it.

`details` JSONB holds sub-tasks as a list `[{title, done}]` so the specialist
can track granular progress without another table.
"""
from __future__ import annotations

from datetime import date as _date
from typing import Any
from uuid import UUID, uuid4

from agno.run.base import RunContext
from agno.tools import tool
from sqlalchemy import select

from src.shared.db import with_user_session
from src.shared.security import utc_now
from src.universe.infrastructure.orm import GoalOrm

VALID_HORIZONS = {"3_months", "6_months", "1_year", "long_term"}
VALID_STATUS = {"active", "paused", "completed", "dropped"}


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


@tool(
    name="add_goal",
    description=(
        "Create a professional goal. `horizon` MUST be one of "
        "'3_months' | '6_months' | '1_year' | 'long_term'. `title` is a short "
        "outcome statement (≤ 80 chars). `description` optional context. "
        "`target_date` is ISO YYYY-MM-DD if a deadline applies. `subtasks` "
        "is an optional list of strings the specialist can break the goal "
        "into; they get stored as `details.subtasks=[{title, done:false}]`."
    ),
)
async def add_goal(
    run_context: RunContext,
    title: str,
    horizon: str,
    description: str | None = None,
    target_date: str | None = None,
    subtasks: list[str] | None = None,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    if horizon not in VALID_HORIZONS:
        return {"ok": False, "error": f"horizon must be one of {sorted(VALID_HORIZONS)}"}
    title = (title or "").strip()
    if not title:
        return {"ok": False, "error": "title cannot be empty"}
    parsed_date: _date | None = None
    if target_date:
        try:
            parsed_date = _date.fromisoformat(target_date)
        except ValueError:
            return {"ok": False, "error": "target_date must be ISO YYYY-MM-DD"}
    details: dict[str, Any] = {}
    if subtasks:
        details["subtasks"] = [
            {"title": s.strip(), "done": False} for s in subtasks if s.strip()
        ]
    async with with_user_session(UUID(user_id)) as session:
        now = utc_now()
        goal = GoalOrm(
            id=uuid4(),
            user_id=UUID(user_id),
            horizon=horizon,
            title=title,
            description=(description or "").strip() or None,
            status="active",
            target_date=parsed_date,
            details=details or None,
            created_at=now,
            updated_at=now,
            completed_at=None,
        )
        session.add(goal)
        await session.refresh(goal)
        return {"ok": True, "goal": _serialize(goal)}


@tool(
    name="list_goals",
    description=(
        "List the user's goals, optionally filtered by status (default: "
        "'active'). Pass status='*' to see all. Returns a list ordered by "
        "target_date asc nulls last, then created_at desc."
    ),
)
async def list_goals(
    run_context: RunContext,
    status: str | None = "active",
    limit: int = 20,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    async with with_user_session(UUID(user_id)) as session:
        stmt = select(GoalOrm).where(GoalOrm.user_id == UUID(user_id))
        if status and status != "*":
            if status not in VALID_STATUS:
                return {"ok": False, "error": f"status must be one of {sorted(VALID_STATUS)} or '*'"}
            stmt = stmt.where(GoalOrm.status == status)
        stmt = stmt.order_by(
            GoalOrm.target_date.asc().nulls_last(),
            GoalOrm.created_at.desc(),
        ).limit(limit)
        rows = (await session.execute(stmt)).scalars().all()
        return {"ok": True, "count": len(rows), "goals": [_serialize(g) for g in rows]}


@tool(
    name="update_goal",
    description=(
        "Patch a goal. Pass any of: title, description, target_date "
        "(ISO YYYY-MM-DD or null to clear), status (active|paused|completed|"
        "dropped), subtasks (full replacement list of strings — wipes "
        "existing). Use `mark_subtask_done(goal_id, subtask_title)` instead "
        "for granular progress."
    ),
)
async def update_goal(
    run_context: RunContext,
    goal_id: str,
    title: str | None = None,
    description: str | None = None,
    target_date: str | None = None,
    status: str | None = None,
    subtasks: list[str] | None = None,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    async with with_user_session(UUID(user_id)) as session:
        goal = (
            await session.execute(
                select(GoalOrm)
                .where(GoalOrm.id == UUID(goal_id))
                .where(GoalOrm.user_id == UUID(user_id))
            )
        ).scalar_one_or_none()
        if goal is None:
            return {"ok": False, "error": "goal not found"}
        if title is not None:
            goal.title = title.strip() or goal.title
        if description is not None:
            goal.description = description.strip() or None
        if target_date is not None:
            if target_date == "":
                goal.target_date = None
            else:
                try:
                    goal.target_date = _date.fromisoformat(target_date)
                except ValueError:
                    return {"ok": False, "error": "target_date must be ISO YYYY-MM-DD"}
        if status is not None:
            if status not in VALID_STATUS:
                return {"ok": False, "error": f"status must be one of {sorted(VALID_STATUS)}"}
            goal.status = status
            if status == "completed":
                goal.completed_at = utc_now()
            elif status != "completed":
                goal.completed_at = None
        if subtasks is not None:
            new_details = dict(goal.details or {})
            new_details["subtasks"] = [
                {"title": s.strip(), "done": False} for s in subtasks if s.strip()
            ]
            goal.details = new_details
        goal.updated_at = utc_now()
        await session.refresh(goal)
        return {"ok": True, "goal": _serialize(goal)}


@tool(
    name="mark_subtask_done",
    description=(
        "Mark a sub-task inside a goal as done (by exact title match). "
        "Idempotent — if it's already done, no-op. Returns the updated goal "
        "and a `progress` percentage (0..100) computed from subtasks."
    ),
)
async def mark_subtask_done(
    run_context: RunContext,
    goal_id: str,
    subtask_title: str,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    async with with_user_session(UUID(user_id)) as session:
        goal = (
            await session.execute(
                select(GoalOrm)
                .where(GoalOrm.id == UUID(goal_id))
                .where(GoalOrm.user_id == UUID(user_id))
            )
        ).scalar_one_or_none()
        if goal is None:
            return {"ok": False, "error": "goal not found"}
        details = dict(goal.details or {})
        subtasks = list(details.get("subtasks", []))
        if not subtasks:
            return {"ok": False, "error": "goal has no subtasks"}
        target = subtask_title.strip().lower()
        matched = False
        for s in subtasks:
            if (s.get("title") or "").strip().lower() == target:
                s["done"] = True
                matched = True
                break
        if not matched:
            return {
                "ok": False,
                "error": f"subtask '{subtask_title}' not found",
                "available": [s.get("title") for s in subtasks],
            }
        details["subtasks"] = subtasks
        goal.details = details
        goal.updated_at = utc_now()
        done = sum(1 for s in subtasks if s.get("done"))
        progress = int(round(100 * done / max(1, len(subtasks))))
        await session.refresh(goal)
        return {"ok": True, "goal": _serialize(goal), "progress": progress}
