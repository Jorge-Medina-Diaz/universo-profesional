"""Billing use cases."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from src.billing.application.ports import (
    PaymentsProvider,
    QuotaRepository,
    SubscriptionRepository,
)
from src.billing.domain.entities import Subscription
from src.shared.errors import NotFoundError, QuotaExceededError
from src.shared.result import Result, err, ok
from src.shared.security import utc_now

ResourceKey = Literal["cv_generated", "cover_letter_generated", "mcp_call"]


def _period_key(resource: str, now: datetime) -> str:
    if resource == "mcp_call":
        return now.strftime("%Y-%m-%d")
    return now.strftime("%Y-%m")


class GetOrCreateSubscription:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: UUID) -> Subscription:
        sub = await self._repo.get(user_id)
        if sub is None:
            sub = Subscription.free_for(user_id, utc_now())
            await self._repo.upsert(sub)
        return sub


class CheckQuota:
    def __init__(self, subs: SubscriptionRepository, quotas: QuotaRepository) -> None:
        self._subs = subs
        self._quotas = quotas

    async def execute(
        self, *, user_id: str, resource: str
    ) -> Result[bool, QuotaExceededError]:
        uid = UUID(user_id)
        sub = await self._subs.get(uid)
        if sub is None:
            sub = Subscription.free_for(uid, utc_now())
            await self._subs.upsert(sub)

        limits = sub.limits
        if resource == "cv_generated":
            cap = limits.monthly_cv
        elif resource == "cover_letter_generated":
            cap = limits.monthly_cover_letters
        elif resource == "mcp_call":
            if not limits.mcp_access:
                return err(QuotaExceededError("MCP access requires Premium or Pro plan"))
            cap = limits.mcp_daily_calls
        else:
            return ok(True)

        if cap == -1:
            return ok(True)

        period = _period_key(resource, utc_now())
        used = await self._quotas.current(uid, resource, period)
        if used >= cap:
            return err(
                QuotaExceededError(
                    f"{resource} quota exceeded ({used}/{cap}); upgrade to Premium for unlimited"
                )
            )
        return ok(True)

    async def increment(self, *, user_id: str, resource: str) -> int:
        uid = UUID(user_id)
        period = _period_key(resource, utc_now())
        return await self._quotas.increment(uid, resource, period)


class StartCheckout:
    def __init__(self, payments: PaymentsProvider) -> None:
        self._payments = payments

    async def execute(self, *, user_id: str, plan: str, return_url: str) -> str:
        return await self._payments.create_checkout(
            user_id=UUID(user_id), plan=plan, return_url=return_url
        )


class StartPortal:
    def __init__(self, payments: PaymentsProvider) -> None:
        self._payments = payments

    async def execute(self, *, user_id: str, return_url: str) -> str:
        return await self._payments.create_portal(
            user_id=UUID(user_id), return_url=return_url
        )


class CancelSubscription:
    def __init__(self, subs: SubscriptionRepository, payments: PaymentsProvider) -> None:
        self._subs = subs
        self._payments = payments

    async def execute(self, *, user_id: str) -> Result[Subscription, NotFoundError]:
        uid = UUID(user_id)
        sub = await self._subs.get(uid)
        if sub is None:
            return err(NotFoundError("No subscription"))
        await self._payments.cancel(user_id=uid)
        sub.status = "canceled"
        sub.cancel_at = utc_now()
        sub.updated_at = utc_now()
        sub.plan = "free"
        await self._subs.upsert(sub)
        return ok(sub)
