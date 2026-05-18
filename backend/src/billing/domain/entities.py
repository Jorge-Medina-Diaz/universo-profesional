"""Billing domain — Subscription aggregate + Plan VO."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

Plan = Literal["free", "premium", "pro"]
SubscriptionStatus = Literal["active", "trialing", "past_due", "canceled"]


@dataclass(frozen=True)
class PlanLimits:
    monthly_cv: int  # -1 = unlimited
    monthly_cover_letters: int
    mcp_access: bool
    mcp_daily_calls: int


PLAN_LIMITS: dict[Plan, PlanLimits] = {
    "free": PlanLimits(monthly_cv=3, monthly_cover_letters=1, mcp_access=False, mcp_daily_calls=0),
    "premium": PlanLimits(
        monthly_cv=-1, monthly_cover_letters=-1, mcp_access=True, mcp_daily_calls=200
    ),
    "pro": PlanLimits(
        monthly_cv=-1, monthly_cover_letters=-1, mcp_access=True, mcp_daily_calls=1000
    ),
}


@dataclass
class Subscription:
    user_id: UUID
    plan: Plan
    status: SubscriptionStatus
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    trial_ends_at: datetime | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @property
    def is_active(self) -> bool:
        return self.status in ("active", "trialing")

    @property
    def is_paying(self) -> bool:
        return self.plan in ("premium", "pro") and self.is_active

    @property
    def limits(self) -> PlanLimits:
        return PLAN_LIMITS[self.plan]

    @classmethod
    def free_for(cls, user_id: UUID, now: datetime) -> "Subscription":
        return cls(
            user_id=user_id,
            plan="free",
            status="active",
            stripe_customer_id=None,
            stripe_subscription_id=None,
            trial_ends_at=None,
            current_period_start=None,
            current_period_end=None,
            cancel_at=None,
            created_at=now,
            updated_at=now,
        )
