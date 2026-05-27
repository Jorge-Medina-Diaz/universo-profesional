"""Temporal snapshot service — reconstruct the universe at a point in time.

Sprint R introduces time-travel for the professional profile: the user (or
an agent) can ask "how did my CV look in March?" and get an accurate
reconstruction.

For the MVP the reconstruction is approximate but useful:
  • Include every entity whose created_at ≤ snapshot_date and that had not
    been soft-deleted by that date (deleted_at IS NULL OR deleted_at > date).
  • We do NOT replay field-level edits from universe_change_log yet; that
    will land in Sprint S once the change-log schema stabilises.
  • Graph edges are filtered by valid_from / valid_to when the graph query
    layer supports it (AGE datetime comparison is best-effort in 1.5).

The returned shape is identical to GetUniverseSummary so the frontend and
 document-generation pipelines can consume it without modification.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.universe.application.ports.orm import (
    AchievementOrm,
    CertificationOrm,
    CourseOrm,
    EducationOrm,
    ExperienceOrm,
    InterestOrm,
    LanguageOrm,
    ProjectOrm,
    SkillOrm,
)


def _as_dict(obj: Any) -> dict[str, Any]:
    """Serialize an ORM row (declarative base) to a plain dict."""
    if hasattr(obj, "__table__"):
        cols = {c.name for c in obj.__table__.columns}
        return {k: _coerce(getattr(obj, k)) for k in cols}
    return dict(obj)


def _coerce(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, list):
        return [_coerce(x) for x in v]
    if isinstance(v, dict):
        return {k: _coerce(val) for k, val in v.items()}
    return v


_ENTITY_TABLES: dict[str, Any] = {
    "educations": EducationOrm,
    "experiences": ExperienceOrm,
    "skills": SkillOrm,
    "projects": ProjectOrm,
    "certifications": CertificationOrm,
    "courses": CourseOrm,
    "languages": LanguageOrm,
    "achievements": AchievementOrm,
    "interests": InterestOrm,
}


class TemporalSnapshotService:
    """Reconstruct a user's universe at a given ISO date."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_universe_at(
        self, *, user_id: UUID, at: datetime
    ) -> dict[str, Any]:
        """Return the universe state as of *at* (inclusive).

        Args:
            user_id: the target user.
            at: UTC datetime.  Only entities that existed at this instant are
                included.
        """
        # Universe header (no temporal versioning yet — return current)
        universe = (
            await self._session.execute(
                text("SELECT * FROM universes WHERE user_id = :uid"),
                {"uid": str(user_id)},
            )
        ).mappings().first()

        header: dict[str, Any] = dict(universe) if universe else {}
        header.pop("user_id", None)
        header = {k: _coerce(v) for k, v in header.items()}

        # Entity snapshot per table
        snapshot: dict[str, list[dict[str, Any]]] = {}
        for key, orm_cls in _ENTITY_TABLES.items():
            table_name = orm_cls.__tablename__
            rows = (
                await self._session.execute(
                    text(
                        f"""
                        SELECT * FROM {table_name}
                        WHERE user_id = :uid
                          AND created_at <= :at
                          AND (deleted_at IS NULL OR deleted_at > :at)
                        ORDER BY created_at
                        """
                    ),
                    {"uid": str(user_id), "at": at},
                )
            ).mappings().all()
            snapshot[key] = [_filter_internal(dict(r)) for r in rows]

        return {
            "snapshot_at": at.isoformat(),
            "header": header,
            **snapshot,
        }

    async def get_document_snapshot_at(
        self, *, user_id: UUID, at: datetime
    ) -> dict[str, Any]:
        """Return documents that existed at *at*, useful for "what CV did I
        generate last month?" queries.
        """
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT id, kind, template, language, tone, job_id,
                           content_json, generated_at, share_token
                    FROM documents
                    WHERE user_id = :uid
                      AND created_at <= :at
                      AND (deleted_at IS NULL OR deleted_at > :at)
                    ORDER BY generated_at DESC
                    """
                ),
                {"uid": str(user_id), "at": at},
            )
        ).mappings().all()
        return {
            "snapshot_at": at.isoformat(),
            "documents": [dict(r) for r in rows],
        }


def _filter_internal(row: dict[str, Any]) -> dict[str, Any]:
    """Drop internal columns that should not leak to the API."""
    drop = {"user_id", "embedding", "deleted_at", "updated_at"}
    return {k: _coerce(v) for k, v in row.items() if k not in drop}
