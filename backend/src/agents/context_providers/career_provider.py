"""CareerContextProvider — Job search, applications, strategy.

Knowledge namespace: "jobs"
Memory scope: "career_strategy"
Tools: job management, application tracking, job matching proposals.

Future expansions (prepared):
  • recruiter knowledge namespace ("recruiters")
  • interview prep tools
  • salary negotiation guidance
"""
from __future__ import annotations

from typing import Any, Callable

from src.agents.context_providers.base import BaseContextProvider
from src.agents.tools.product_reads import list_jobs
from src.agents.tools.ui_widgets import (
    present_job_match,
    propose_autopilot_run,
    propose_job_create,
    propose_job_status_change,
)


class CareerContextProvider(BaseContextProvider):
    name = "career_strategist"
    knowledge_namespace = "jobs"
    memory_scope = "career_strategy"

    def get_tools(self) -> list[Callable[..., Any]]:
        return [
            list_jobs,
            propose_job_create,
            propose_job_status_change,
            propose_autopilot_run,
            present_job_match,
        ]
