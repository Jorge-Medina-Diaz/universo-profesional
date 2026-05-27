"""Application-layer ports for llm_tracking."""
from __future__ import annotations

from typing import Protocol

from src.llm_tracking.domain.entities import LlmUsageLog


class LlmUsageLogRepository(Protocol):
    async def create(self, log: LlmUsageLog) -> None: ...
