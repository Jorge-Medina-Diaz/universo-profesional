"""Structured Memory — 4-tier persistence for agent context.

Complements Agno's native memory (session runs + auto-extracted memories)
with domain-specific schemas that the Context Providers read and write
directly.

Tiers:
  • Semantic  — Facts about the user (preferences, goals, skill gaps).
  • Procedural — Learned rules / patterns ("user prefers functional CVs",
                "always ask before deleting a skill").
  • Episodic  — Session summaries with extracted entities, open questions,
                decisions, mood.
  • Working   — Lives in Agno's session_state (not persisted here).

All tables are RLS-isolated per user.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Float, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db import Base


# ---------------------------------------------------------------------------
# ORM models
# ---------------------------------------------------------------------------


class UserSemanticMemoryOrm(Base):
    """Facts about the user: preferences, goals, inferred traits."""

    __tablename__ = "user_semantic_memory"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="agent_inference")
    last_confirmed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class UserProceduralMemoryOrm(Base):
    """Learned rules that guide agent behaviour per scope."""

    __tablename__ = "user_procedural_memory"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    action_rule: Mapped[str] = mapped_column(Text, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class SessionEpisodeOrm(Base):
    """Compressed episode of a chat session."""

    __tablename__ = "session_episodes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_facts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    open_questions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    decisions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    mentioned_entities: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    mood: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


# ---------------------------------------------------------------------------
# Domain dataclasses (pure, no DB dependency)
# ---------------------------------------------------------------------------


@dataclass
class SemanticFact:
    category: str
    key: str
    value: str
    confidence: float = 0.8
    source: str = "agent_inference"


@dataclass
class ProceduralRule:
    scope: str
    trigger_pattern: str
    action_rule: str
    hit_count: int = 0
    success_rate: float = 1.0
    active: bool = True


@dataclass
class Episode:
    session_id: str
    summary: str
    extracted_facts: list[SemanticFact] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    mentioned_entities: list[dict[str, Any]] = field(default_factory=list)
    mood: str | None = None
