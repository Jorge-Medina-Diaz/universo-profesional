"""Per-stage latency timing for the AG-UI chat round-trip.

One `RunTimer` is created per /run request and threaded through the stream
pipeline. Each stage is marked once (first occurrence wins) and observed on
the `cvs_agent_stage_seconds{stage}` histogram immediately, so a run that
dies mid-stream still reports the stages it reached. `finish()` emits a
single structlog line with the full breakdown for request-level debugging.

Stage map (elapsed from request start):
  auth_done      JWT decoded
  validated      AG-UI payload validated + caps applied
  team_resolved  build_team_for_user returned (cache hit ≈ 0)
  intent_done    IntentRouter classification + provider context done
  run_started    team.arun stream opened
  ttft           first user-visible frame (assistant text delta OR tool-call
                 start) — the "feels alive" moment the plan optimizes for
  stream_done    last frame emitted (RUN_FINISHED or error close)
"""
from __future__ import annotations

import time

import structlog

from src.shared.metrics import agent_stage_seconds

logger = structlog.get_logger(__name__)

STAGES = (
    "auth_done",
    "validated",
    "team_resolved",
    "intent_done",
    "run_started",
    "ttft",
    "stream_done",
)


class RunTimer:
    __slots__ = ("_t0", "marks")

    def __init__(self) -> None:
        self._t0 = time.monotonic()
        self.marks: dict[str, float] = {}

    def mark(self, stage: str) -> None:
        """Record a stage once; later calls for the same stage are no-ops."""
        if stage in self.marks:
            return
        elapsed = time.monotonic() - self._t0
        self.marks[stage] = elapsed
        try:
            agent_stage_seconds.labels(stage=stage).observe(elapsed)
        except Exception:  # metrics must never break the stream
            logger.warning("stage_metric_failed", stage=stage)

    def finish(self, *, user_id: str, status: str) -> None:
        self.mark("stream_done")
        logger.info(
            "agent_run_stages",
            user_id=user_id,
            status=status,
            **{k: round(v, 3) for k, v in self.marks.items()},
        )
