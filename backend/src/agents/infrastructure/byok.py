"""BYOK — per-user LLM API keys, encrypted at rest.

A Pro user can supply their own Anthropic/OpenAI key so their agent usage runs
on their account/quota. The key is Fernet-encrypted (same primitive as OAuth
tokens + MFA secrets) and resolved at team-build time by `agents.factory`.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db import Base, with_user_session
from src.shared.fernet import decrypt, encrypt
from src.shared.security import utc_now

logger = structlog.get_logger(__name__)

VALID_PROVIDERS = ("anthropic", "openai")


class UserLlmCredentialOrm(Base):
    __tablename__ = "user_llm_credentials"

    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


async def set_credential(
    session: AsyncSession, *, user_id: UUID, provider: str, api_key: str
) -> None:
    enc = encrypt(api_key).decode("ascii")
    now = utc_now()
    row = await session.get(UserLlmCredentialOrm, user_id)
    if row is None:
        session.add(
            UserLlmCredentialOrm(
                user_id=user_id,
                provider=provider,
                encrypted_key=enc,
                created_at=now,
                updated_at=now,
            )
        )
    else:
        row.provider = provider
        row.encrypted_key = enc
        row.updated_at = now
    await session.flush()


async def get_credential_status(
    session: AsyncSession, user_id: UUID
) -> tuple[bool, str | None]:
    """(configured, provider) — never returns the key itself."""
    row = await session.get(UserLlmCredentialOrm, user_id)
    return (row is not None, row.provider if row else None)


async def delete_credential(session: AsyncSession, user_id: UUID) -> bool:
    row = await session.get(UserLlmCredentialOrm, user_id)
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


async def resolve_user_llm_credential(user_id: str) -> tuple[str, str] | None:
    """(provider, decrypted_api_key) for the factory, or None.

    Opens its own RLS-scoped session so it can be called outside a request
    context (the factory builds the team before the request session is handed
    in). Any failure returns None so the chat falls back to the platform key.
    """
    try:
        async with with_user_session(UUID(user_id)) as session:
            row = await session.get(UserLlmCredentialOrm, UUID(user_id))
            if row is None:
                return None
            return row.provider, decrypt(row.encrypted_key.encode("ascii"))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("byok_resolve_failed", error=str(exc))
        return None
