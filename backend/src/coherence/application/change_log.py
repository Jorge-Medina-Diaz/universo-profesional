"""Thin helper around `ChangeLogRepository` — turns a `MergePlan` into N
field-level entries, plus a single `create`/`delete` shortcut.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from src.coherence.application.ports import ChangeLogRepository
from src.coherence.domain.upsert_decision import FieldDiff


async def record_create(
    repo: ChangeLogRepository,
    *,
    user_id: UUID,
    entity_type: str,
    entity_id: UUID,
    new_value: dict[str, Any],
    source: str,
    reason: str | None = None,
    agent_run_id: str | None = None,
) -> None:
    await repo.record(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        change_type="create",
        field=None,
        old_value=None,
        new_value=new_value,
        reason=reason,
        source=source,
        agent_run_id=agent_run_id,
    )


async def record_delete(
    repo: ChangeLogRepository,
    *,
    user_id: UUID,
    entity_type: str,
    entity_id: UUID,
    old_value: dict[str, Any],
    source: str,
    reason: str | None = None,
    agent_run_id: str | None = None,
) -> None:
    await repo.record(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        change_type="delete",
        field=None,
        old_value=old_value,
        new_value=None,
        reason=reason,
        source=source,
        agent_run_id=agent_run_id,
    )


async def record_merge(
    repo: ChangeLogRepository,
    *,
    user_id: UUID,
    entity_type: str,
    entity_id: UUID,
    diffs: list[FieldDiff],
    source: str,
    reason: str | None = None,
    agent_run_id: str | None = None,
) -> None:
    """One row per field changed during a merge.

    Empty diffs → no-op (we skip writing entirely so the log stays meaningful).
    """
    for d in diffs:
        await repo.record(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            change_type="update",
            field=d.field,
            old_value=_jsonify(d.old),
            new_value=_jsonify(d.new),
            reason=reason,
            source=source,
            agent_run_id=agent_run_id,
        )


def _jsonify(v: Any) -> Any:
    """Coerce values to JSON-safe primitives for JSONB columns."""
    from datetime import date, datetime
    from uuid import UUID as _UUID

    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, _UUID):
        return str(v)
    if isinstance(v, list):
        return [_jsonify(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonify(val) for k, val in v.items()}
    return v
