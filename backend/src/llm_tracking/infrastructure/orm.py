"""SQLAlchemy ORM for llm_usage_logs."""
from __future__ import annotations

import uuid

from sqlalchemy import Column, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

from src.shared.db import Base


class LlmUsageLogORM(Base):
    __tablename__ = "llm_usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    run_id = Column(String(64), nullable=True)
    session_id = Column(String(128), nullable=True)
    provider = Column(String(32), nullable=False)
    model = Column(String(64), nullable=False)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    cache_read_tokens = Column(Integer, nullable=False, default=0)
    cache_write_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=True)
    cost_eur = Column(Numeric(12, 8), nullable=True)
    agent = Column(String(64), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
