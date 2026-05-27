"""Generic SQLAlchemy CRUD base and factory."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.security import utc_now


def _entity_to_orm_kwargs(entity: Any, orm_cls: Any) -> dict[str, Any]:
    """Pick fields from the dataclass entity that exist on the ORM class."""
    orm_cols = {c.name for c in orm_cls.__table__.columns}
    out: dict[str, Any] = {}
    for f in entity.__dataclass_fields__:
        if f.startswith("_"):
            continue
        if f in orm_cols:
            out[f] = getattr(entity, f)
    return out


def _orm_to_entity(row: Any, entity_cls: Any) -> Any:
    """Map ORM row → entity dataclass. Fields not present on the entity are dropped."""
    fields = {f for f in entity_cls.__dataclass_fields__ if not f.startswith("_")}
    kwargs = {f: getattr(row, f) for f in fields if hasattr(row, f)}
    return entity_cls(**kwargs)


def _build_repo_methods(orm_cls: Any, entity_cls: Any) -> dict[str, Any]:
    """Return a dict of methods implementing the standard repo Protocol."""

    async def list_(self: Any, user_id: UUID) -> list[Any]:
        stmt = select(orm_cls).where(orm_cls.user_id == user_id)
        if hasattr(orm_cls, "deleted_at"):
            stmt = stmt.where(orm_cls.deleted_at.is_(None))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_orm_to_entity(r, entity_cls) for r in rows]

    async def get_(self: Any, user_id: UUID, entity_id: UUID) -> Any | None:
        stmt = select(orm_cls).where(orm_cls.id == entity_id).where(orm_cls.user_id == user_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return _orm_to_entity(row, entity_cls)

    async def add_(self: Any, entity: Any) -> None:
        self._session.add(orm_cls(**_entity_to_orm_kwargs(entity, orm_cls)))
        await self._session.flush()

    async def update_(self: Any, entity: Any) -> None:
        existing = await self._session.get(orm_cls, entity.id)
        if existing is None:
            return
        for k, v in _entity_to_orm_kwargs(entity, orm_cls).items():
            setattr(existing, k, v)
        existing.updated_at = utc_now()
        await self._session.flush()

    async def delete_(self: Any, user_id: UUID, entity_id: UUID) -> bool:
        stmt = (
            delete(orm_cls)
            .where(orm_cls.id == entity_id)
            .where(orm_cls.user_id == user_id)
            .returning(orm_cls.id)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def update_embedding_(self: Any, entity_id: UUID, embedding: list[float]) -> None:
        stmt = (
            update(orm_cls)
            .where(orm_cls.id == entity_id)
            .values(embedding=embedding, updated_at=utc_now())
        )
        await self._session.execute(stmt)
        await self._session.flush()

    return {
        "list": list_,
        "get": get_,
        "add": add_,
        "update": update_,
        "delete": delete_,
        "update_embedding": update_embedding_,
    }


class _BaseRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session


def _make_repo(name: str, orm_cls: Any, entity_cls: Any) -> type:
    methods = _build_repo_methods(orm_cls, entity_cls)
    return type(name, (_BaseRepo,), methods)
