"""Concrete `ChangeLogRepository` over SQLAlchemy + Postgres."""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.coherence.application.ports import ChangeLogRepository


class SqlAlchemyChangeLogRepository(ChangeLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        user_id: UUID,
        entity_type: str,
        entity_id: UUID,
        change_type: str,
        field: str | None,
        old_value: Any,
        new_value: Any,
        reason: str | None,
        source: str,
        agent_run_id: str | None = None,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO universe_change_log (
                    id, user_id, entity_type, entity_id, change_type, field,
                    old_value, new_value, reason, source, agent_run_id, changed_at
                ) VALUES (
                    :id, :user_id, :etype, :eid, :ctype, :field,
                    CAST(:oldv AS jsonb), CAST(:newv AS jsonb), :reason, :source, :run_id, now()
                )
                """
            ),
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "etype": entity_type,
                "eid": str(entity_id),
                "ctype": change_type,
                "field": field,
                "oldv": _to_json(old_value),
                "newv": _to_json(new_value),
                "reason": reason,
                "source": source,
                "run_id": agent_run_id,
            },
        )

    async def list_for_user(
        self, *, user_id: UUID, limit: int = 50, since: Any | None = None
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT id::text, entity_type, entity_id::text, change_type, field,
                   old_value, new_value, reason, source, agent_run_id, changed_at
            FROM universe_change_log
            WHERE user_id = :uid
        """
        params: dict[str, Any] = {"uid": str(user_id), "limit": limit}
        if since is not None:
            sql += " AND changed_at >= :since"
            params["since"] = since
        sql += " ORDER BY changed_at DESC LIMIT :limit"
        rows = (await self._session.execute(text(sql), params)).mappings().all()
        return [dict(r) for r in rows]

    async def list_for_entity(
        self,
        *,
        user_id: UUID,
        entity_type: str,
        entity_id: UUID,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT id::text, change_type, field, old_value, new_value, reason,
                   source, agent_run_id, changed_at
            FROM universe_change_log
            WHERE user_id = :uid AND entity_type = :etype AND entity_id = :eid
            ORDER BY changed_at DESC LIMIT :limit
        """
        rows = (
            await self._session.execute(
                text(sql),
                {
                    "uid": str(user_id),
                    "etype": entity_type,
                    "eid": str(entity_id),
                    "limit": limit,
                },
            )
        ).mappings().all()
        return [dict(r) for r in rows]


def _to_json(v: Any) -> str | None:
    """Serialize Python value to a JSON string (asyncpg/JSONB friendly)."""
    if v is None:
        return None
    import json

    return json.dumps(v, default=str)
