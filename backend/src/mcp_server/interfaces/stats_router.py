"""MCP stats REST API: /api/v1/mcp/stats"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import func, select

from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.mcp_server.infrastructure.orm import McpInvocationOrm

router = APIRouter()


@router.get("/stats")
async def get_mcp_stats(user_id: CurrentUserId, session: SessionDep) -> dict[str, Any]:
    user_uuid = UUID(user_id)

    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    recent_start = now - timedelta(days=7)

    # Total invocations
    total_result = await session.execute(
        select(func.count())
        .select_from(McpInvocationOrm)
        .where(McpInvocationOrm.user_id == user_uuid)
    )
    total_invocations = total_result.scalar_one()

    # Invocations today
    today_result = await session.execute(
        select(func.count())
        .select_from(McpInvocationOrm)
        .where(McpInvocationOrm.user_id == user_uuid)
        .where(McpInvocationOrm.created_at >= today_start)
    )
    invocations_today = today_result.scalar_one()

    # Invocations this week
    week_result = await session.execute(
        select(func.count())
        .select_from(McpInvocationOrm)
        .where(McpInvocationOrm.user_id == user_uuid)
        .where(McpInvocationOrm.created_at >= week_start)
    )
    invocations_this_week = week_result.scalar_one()

    # Top tools
    top_tools_result = await session.execute(
        select(McpInvocationOrm.tool_name, func.count())
        .where(McpInvocationOrm.user_id == user_uuid)
        .group_by(McpInvocationOrm.tool_name)
        .order_by(func.count().desc())
        .limit(5)
    )
    top_tools = [
        {"tool_name": row[0], "count": row[1]}
        for row in top_tools_result.all()
    ]

    # Recent errors (last 7 days)
    errors_result = await session.execute(
        select(func.count())
        .select_from(McpInvocationOrm)
        .where(McpInvocationOrm.user_id == user_uuid)
        .where(McpInvocationOrm.ok.is_(False))
        .where(McpInvocationOrm.created_at >= recent_start)
    )
    recent_errors = errors_result.scalar_one()

    return {
        "total_invocations": total_invocations,
        "invocations_today": invocations_today,
        "invocations_this_week": invocations_this_week,
        "top_tools": top_tools,
        "recent_errors": recent_errors,
    }
