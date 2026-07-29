"""Query use cases — search, list, filter, summary, and other one-off reads."""
from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID

from src.shared.errors import NotFoundError, ValidationError
from src.shared.redis import get_redis
from src.shared.result import Result, err, ok
from src.shared.uow import UnitOfWork
from src.universe.application.crud import _serialize
from src.universe.application.ports import (
    CareerPreferencesRepository,
    EducationRepository,
    ExperienceRepository,
    LanguageRepository,
    ProjectRepository,
    SemanticSearchPort,
    SkillRepository,
    UniverseRepository,
)
from src.universe.domain.entities import CareerPreferences
from src.universe.domain.universe import Universe

# --- Universe summary ------------------------------------------------------


class GetUniverseSummary:
    def __init__(
        self,
        universes: UniverseRepository,
        educations: EducationRepository,
        experiences: ExperienceRepository,
        skills: SkillRepository,
        languages: LanguageRepository,
        projects: ProjectRepository,
        prefs: CareerPreferencesRepository,
    ) -> None:
        self._universes = universes
        self._edu = educations
        self._exp = experiences
        self._skills = skills
        self._lang = languages
        self._proj = projects
        self._prefs = prefs

    async def execute(self, *, user_id: str) -> dict[str, Any]:
        cache_key = f"universe:summary:{user_id}"
        redis = get_redis()
        try:
            cached = await redis.get(cache_key)
            if cached:
                import json

                return json.loads(cached)
        except Exception:
            # Cache miss or Redis unavailable — fall through to DB
            pass

        uid = UUID(user_id)
        universe = await self._universes.get(uid)
        if universe is None:
            universe = Universe.for_user(uid)
            await self._universes.save(universe)
        edu = await self._edu.list(uid)
        exp = await self._exp.list(uid)
        skills = await self._skills.list(uid)
        langs = await self._lang.list(uid)
        projs = await self._proj.list(uid)
        prefs = await self._prefs.get(uid)
        result = {
            "headline": universe.headline,
            "summary": universe.summary,
            "photo_url": universe.photo_url,
            "current_status": universe.current_status,
            "counts": {
                "educations": len(edu),
                "experiences": len(exp),
                "projects": len(projs),
                "skills": len(skills),
                "languages": len(langs),
            },
            "top_skills": [_serialize(s) for s in skills[:8]],
            "recent_experiences": [_serialize(e) for e in exp[:3]],
            "languages": [_serialize(lang) for lang in langs],
            "preferences": _serialize(prefs) if prefs else None,
        }

        try:
            import json

            await redis.setex(cache_key, 30, json.dumps(result))
        except Exception:
            pass

        return result


# --- CareerPreferences -----------------------------------------------------


class SetCareerPreferences:
    def __init__(self, repo: CareerPreferencesRepository) -> None:
        self._repo = repo

    async def execute(self, *, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        existing = await self._repo.get(UUID(user_id))
        from datetime import UTC as _UTC
        from datetime import datetime as _dt

        if existing is None:
            existing = CareerPreferences(user_id=UUID(user_id))
        for k, v in patch.items():
            if hasattr(existing, k):
                setattr(existing, k, v)
        existing.updated_at = _dt.now(_UTC)
        await self._repo.upsert(existing)
        return _serialize(existing)


class GetCareerPreferences:
    def __init__(self, repo: CareerPreferencesRepository) -> None:
        self._repo = repo

    async def execute(self, *, user_id: str) -> dict[str, Any] | None:
        existing = await self._repo.get(UUID(user_id))
        return _serialize(existing) if existing else None


# --- Universe-level update -------------------------------------------------


class UpdateUniverseHeader:
    def __init__(self, repo: UniverseRepository) -> None:
        self._repo = repo

    async def execute(
        self, *, user_id: str, patch: dict[str, Any], uow: UnitOfWork
    ) -> dict[str, Any]:
        from datetime import UTC as _UTC
        from datetime import datetime as _dt

        uid = UUID(user_id)
        universe = await self._repo.get(uid)
        if universe is None:
            universe = Universe.for_user(uid)
        universe.update(
            headline=patch.get("headline", ...),
            summary=patch.get("summary", ...),
            photo_url=patch.get("photo_url", ...),
            current_status=patch.get("current_status", ...),
            now=_dt.now(_UTC),
        )
        await self._repo.save(universe)
        uow.add_events(universe.pop_events())
        return {
            "user_id": str(universe.user_id),
            "headline": universe.headline,
            "summary": universe.summary,
            "photo_url": universe.photo_url,
            "current_status": universe.current_status,
        }


# --- Semantic search -------------------------------------------------------


class SearchUniverse:
    def __init__(
        self,
        search: SemanticSearchPort,
        embedder: Any,  # EmbeddingsProvider
    ) -> None:
        self._search = search
        self._embed = embedder

    async def execute(
        self, *, user_id: str, query: str, top_k: int = 10, entity_types: list[str] | None = None
    ) -> list[dict[str, Any]]:
        vec = await self._embed.embed(query)
        return await self._search.search(
            user_id=UUID(user_id),
            embedding=vec,
            top_k=top_k,
            entity_types=entity_types,
        )


# --- MarkReviewed -----------------------------------------------------------


class MarkReviewed:
    """Touch `last_reviewed_at` on an entity. Confirms the user has inspected it recently."""

    _TABLE_BY_TYPE: ClassVar[dict[str, str]] = {
        "education": "educations",
        "experience": "experiences",
        "project": "projects",
        "skill": "skills",
        "certification": "certifications",
        "course": "courses",
        "language": "languages",
        "achievement": "achievements",
        "interest": "interests",
        # Sprint G/K
        "artifact": "artifacts",
        "architecture_decision": "architecture_decisions",
    }

    def __init__(self, session: Any) -> None:
        self._session = session

    async def execute(
        self, *, user_id: str, entity_type: str, entity_id: str
    ) -> Result[dict[str, str], NotFoundError | ValidationError]:
        from sqlalchemy import text

        table = self._TABLE_BY_TYPE.get(entity_type)
        if table is None:
            return err(ValidationError(f"Unknown entity_type {entity_type!r}"))
        stmt = text(
            f"UPDATE {table} SET last_reviewed_at = now() "
            f"WHERE id = :eid AND user_id = :uid RETURNING id"
        )
        result = await self._session.execute(
            stmt, {"eid": entity_id, "uid": user_id}
        )
        row = result.first()
        if row is None:
            return err(NotFoundError(f"{entity_type} not found"))
        return ok({"entity_type": entity_type, "entity_id": entity_id, "reviewed_at": "now"})


# --- GetActivity ------------------------------------------------------------


class GetActivity:
    """Read from domain_events table (populated by activity_log subscriber)."""

    def __init__(self, session: Any) -> None:
        self._session = session

    async def execute(
        self,
        *,
        user_id: str,
        limit: int = 50,
        since: str | None = None,
        event_types: list[str] | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        from sqlalchemy import text

        from src.shared.pagination import build_page, decode_cursor

        # Fetch limit+1 to detect a next page; a stable (occurred_at, event_id)
        # tiebreaker prevents dup/skip when many events share a timestamp.
        params: dict[str, Any] = {"uid": user_id, "limit": limit + 1}
        where = ["user_id = :uid"]
        if since:
            where.append("occurred_at >= :since")
            params["since"] = since
        if event_types:
            placeholders = ",".join(f":et{i}" for i in range(len(event_types)))
            where.append(f"event_type IN ({placeholders})")
            for i, et in enumerate(event_types):
                params[f"et{i}"] = et
        cur = decode_cursor(cursor)
        if cur:
            where.append(
                "(occurred_at, event_id) < (CAST(:c_ts AS timestamptz), CAST(:c_id AS uuid))"
            )
            params["c_ts"], params["c_id"] = cur
        stmt = text(
            "SELECT event_id::text, event_type, occurred_at, payload "
            "FROM domain_events "
            f"WHERE {' AND '.join(where)} "
            "ORDER BY occurred_at DESC, event_id DESC LIMIT :limit"
        )
        rows = await self._session.execute(stmt, params)
        items = [
            {
                "event_id": r[0],
                "event_type": r[1],
                "occurred_at": r[2].isoformat() if r[2] else None,
                "payload": r[3],
            }
            for r in rows.fetchall()
        ]
        return build_page(items, limit, ts_key="occurred_at", id_key="event_id")


# --- Evidence linking -------------------------------------------------------


class LinkEvidence:
    """Create a skill ↔ entity evidence link with weight."""

    def __init__(self, session: Any) -> None:
        self._session = session

    async def execute(
        self,
        *,
        user_id: str,
        skill_id: str,
        evidence_entity_type: str,
        evidence_entity_id: str,
        weight: float = 1.0,
        notes: str | None = None,
    ) -> Result[dict[str, Any], ValidationError]:
        from uuid import uuid4

        from src.shared.security import utc_now
        from src.universe.application.ports.orm import EvidenceOrm

        if evidence_entity_type not in {"experience", "project", "achievement", "certification", "course"}:
            return err(ValidationError(f"Unknown evidence type {evidence_entity_type!r}"))
        ev = EvidenceOrm(
            id=uuid4(),
            user_id=UUID(user_id),
            skill_id=UUID(skill_id),
            evidence_entity_type=evidence_entity_type,
            evidence_entity_id=UUID(evidence_entity_id),
            weight=weight,
            notes=notes,
            created_at=utc_now(),
        )
        self._session.add(ev)
        await self._session.flush()
        return ok({"id": str(ev.id)})


class ListEvidence:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def execute(self, *, user_id: str, skill_id: str | None = None) -> list[dict[str, Any]]:
        from sqlalchemy import desc as sa_desc
        from sqlalchemy import select

        from src.universe.application.ports.orm import EvidenceOrm

        stmt = (
            select(EvidenceOrm)
            .where(EvidenceOrm.user_id == UUID(user_id))
            .order_by(sa_desc(EvidenceOrm.created_at))
        )
        if skill_id:
            stmt = stmt.where(EvidenceOrm.skill_id == UUID(skill_id))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "id": str(r.id),
                "skill_id": str(r.skill_id),
                "evidence_entity_type": r.evidence_entity_type,
                "evidence_entity_id": str(r.evidence_entity_id),
                "weight": r.weight,
                "notes": r.notes,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
