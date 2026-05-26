"""SQLAlchemy ORM for MCP OAuth tables."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db import Base


class OAuthClientOrm(Base):
    __tablename__ = "oauth_clients"

    client_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    client_name: Mapped[str] = mapped_column(Text, nullable=False)
    redirect_uris: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    grant_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    client_secret_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_endpoint_auth_method: Mapped[str] = mapped_column(Text, nullable=False, default="none")
    software_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    software_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class OAuthAuthorizationCodeOrm(Base):
    __tablename__ = "oauth_authorization_codes"

    code_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("oauth_clients.client_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    resource: Mapped[str] = mapped_column(Text, nullable=False)
    code_challenge: Mapped[str] = mapped_column(Text, nullable=False)
    code_challenge_method: Mapped[str] = mapped_column(Text, nullable=False, default="S256")
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


class OAuthTokenOrm(Base):
    __tablename__ = "oauth_tokens"

    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("oauth_clients.client_id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    resource: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    replaced_by: Mapped[str | None] = mapped_column(Text, nullable=True)


class McpInvocationOrm(Base):
    __tablename__ = "mcp_invocations"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    tool_name: Mapped[str] = mapped_column(Text, nullable=False)
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
