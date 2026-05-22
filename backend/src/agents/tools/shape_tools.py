"""Polyglot shape tools: get the user's T/π/M-shape + manage artifacts.

These tools are the canonical access point to the polyglot foundation
introduced in migration 0011. They wrap:

  - `shape_service` for area_strengths (read + recompute).
  - `SqlAlchemyArtifactRepository` for portfolio-citizen artifacts.

The `propose_artifact` HITL tool lives in `ui_widgets.py` (external
execution by the React layer).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agno.run.base import RunContext
from agno.tools import tool

from src.shared.db import get_session_factory, set_rls_user
from src.universe.application.shape_service import (
    _infer_shape,
    compute_area_strengths,
    load_area_strengths,
)
from src.universe.domain.entities import Artifact
from src.universe.infrastructure.repositories import (
    SqlAlchemyArtifactRepository,
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@tool(
    name="get_universe_shape",
    description=(
        "Read the user's polyglot shape (T/π/M-shape) from persisted "
        "`area_strengths`. Returns {shape_type, primary_areas[], "
        "secondary_areas[], strengths: [{area, depth_years, breadth_count, "
        "recency_months, confidence, is_primary}], computed_at}. "
        "shape_type ∈ {I, T, π, M, none}. Cold path (no cache) recomputes "
        "from skills+projects+experiences. Use this BEFORE generating "
        "area-specific narrative — it grounds you in real data."
    ),
)
async def get_universe_shape(run_context: RunContext) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    user_uuid = UUID(user_id)
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, user_uuid)
        strengths, primary, secondary = await load_area_strengths(session, user_uuid)
        if not strengths:
            result = await compute_area_strengths(session, user_uuid)
            await session.commit()
            strengths = result.strengths
            primary = result.primary_areas[0] if result.primary_areas else None
            secondary = result.secondary_areas
    primary_areas = [s.area for s in strengths if s.is_primary]
    scores = {s.area: s.confidence for s in strengths}
    shape_type = _infer_shape(scores, primary_areas)
    return {
        "ok": True,
        "shape_type": shape_type,
        "primary_area": primary,
        "primary_areas": primary_areas,
        "secondary_areas": secondary,
        "strengths": [
            {
                "area": s.area,
                "depth_years": float(s.depth_years),
                "breadth_count": s.breadth_count,
                "recency_months": s.recency_months,
                "confidence": float(s.confidence),
                "is_primary": s.is_primary,
            }
            for s in sorted(strengths, key=lambda x: x.confidence, reverse=True)
        ],
    }


@tool(
    name="recompute_universe_shape",
    description=(
        "Force recompute of the user's polyglot shape. Use after bulk "
        "imports (LinkedIn / PDF CV) or when the user explicitly asks to "
        "refresh their radar. Idempotent."
    ),
)
async def recompute_universe_shape(run_context: RunContext) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    user_uuid = UUID(user_id)
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, user_uuid)
        result = await compute_area_strengths(session, user_uuid)
        await session.commit()
    return {
        "ok": True,
        "shape_type": result.shape_type,
        "primary_areas": result.primary_areas,
        "secondary_areas": result.secondary_areas,
        "strengths_count": len(result.strengths),
    }


@tool(
    name="list_artifacts",
    description=(
        "List the user's portfolio artifacts (github_repo, talk, blog_post, "
        "oss_contrib, paper, podcast, video, book, other). Optional filter "
        "by `type`. Returns {ok, artifacts: [{id, type, title, url, year, "
        "description, venue}]}. For an artifact's linked project/skills use "
        "`get_graph_neighbors`. Read-only."
    ),
)
async def list_artifacts(
    run_context: RunContext,
    type: str | None = None,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    user_uuid = UUID(user_id)
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, user_uuid)
        repo = SqlAlchemyArtifactRepository(session)
        artifacts = await repo.list(user_uuid, type=type)
    return {
        "ok": True,
        "count": len(artifacts),
        "artifacts": [
            {
                "id": str(a.id),
                "type": a.type,
                "title": a.title,
                "url": a.url,
                "year": a.year,
                "description": a.description,
                "venue": a.venue,
            }
            for a in artifacts
        ],
    }


@tool(
    name="upsert_artifact",
    description=(
        "Persist an artifact (github_repo|talk|blog_post|oss_contrib|paper|"
        "podcast|video|book|other) to the user's portfolio. Server-side "
        "write — call AFTER the user approved a `propose_artifact` HITL "
        "card. type, title, url required."
    ),
)
async def upsert_artifact(
    run_context: RunContext,
    type: str,
    title: str,
    url: str,
    year: int | None = None,
    description: str | None = None,
    venue: str | None = None,
    linked_project_id: str | None = None,
    linked_skill_ids: list[str] | None = None,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    user_uuid = UUID(user_id)

    skill_uuids: list[UUID] = []
    if linked_skill_ids:
        try:
            skill_uuids = [UUID(s) for s in linked_skill_ids if s]
        except ValueError as exc:
            return {"ok": False, "error": f"invalid linked_skill_ids: {exc}"}

    project_uuid: UUID | None = None
    if linked_project_id:
        try:
            project_uuid = UUID(linked_project_id)
        except ValueError as exc:
            return {"ok": False, "error": f"invalid linked_project_id: {exc}"}

    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, user_uuid)
        repo = SqlAlchemyArtifactRepository(session)
        artifact = Artifact.create(
            user_id=user_uuid,
            type=type,
            title=title,
            url=url,
            year=year,
            description=description,
            venue=venue,
        )
        artifact.source = "agent_chat"
        artifact.created_at = _now_utc()
        artifact.updated_at = _now_utc()
        await repo.add(artifact)

        # Mirror to the graph + materialise relation edges. linked_* are
        # no longer artifact columns (migration 0017) — they're graph
        # edges (:USES_TECH to skills, :PART_OF to a project).
        from src.graph.application.universe_graph import universe_graph_service
        from src.graph.domain import schema as gschema

        await universe_graph_service.upsert_entity(
            session,
            entity_id=artifact.id,
            user_id=user_uuid,
            kind="artifact",
            source="agent_chat",
        )
        for sid in skill_uuids:
            await universe_graph_service.upsert_edge(
                session,
                edge_type=gschema.USES_TECH,
                source_id=artifact.id,
                target_id=sid,
                user_id=user_uuid,
                source="agent_chat",
            )
        if project_uuid is not None:
            await universe_graph_service.upsert_edge(
                session,
                edge_type=gschema.PART_OF,
                source_id=artifact.id,
                target_id=project_uuid,
                user_id=user_uuid,
                source="agent_chat",
            )
        await session.commit()
    return {
        "ok": True,
        "status": "created",
        "artifact_id": str(artifact.id),
        "type": artifact.type,
        "title": artifact.title,
        "url": artifact.url,
    }
