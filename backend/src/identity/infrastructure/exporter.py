"""RGPD Art. 20 exporter — dumps every row owned by the user."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.identity.application.ports import UserDataExporter

EXPORT_TABLES = (
    "users",
    "universes",
    "educations",
    "experiences",
    "projects",
    "skills",
    "certifications",
    "courses",
    "languages",
    "achievements",
    "interests",
    "career_preferences",
    "goals",
    "documents",
    "jobs",
    "applications",
    "subscriptions",
)


class SqlUserDataExporter(UserDataExporter):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # The owning column is `user_id` on every table except `users` itself,
    # where it's the primary key `id`. The old `WHERE user_id = :uid OR id = :uid`
    # raised "column user_id does not exist" on `users`, silently dropping the
    # account row from the GDPR Art. 20 export (and double-counted elsewhere).
    _TABLE_USER_COL: dict[str, str] = {"users": "id"}

    async def export_all(self, user_id: UUID) -> dict[str, Any]:
        out: dict[str, Any] = {"user_id": str(user_id), "tables": {}}
        for table in EXPORT_TABLES:
            col = self._TABLE_USER_COL.get(table, "user_id")
            stmt = text(f"SELECT row_to_json(t) AS row FROM {table} t WHERE {col} = :uid")
            try:
                rows = (await self._session.execute(stmt, {"uid": str(user_id)})).all()
                out["tables"][table] = [r[0] for r in rows]
            except Exception as exc:
                out["tables"][table] = {"error": str(exc)}
        return out
