"""Billing API: /api/v1/billing/*"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Body
from pydantic import BaseModel

from src.billing.application.use_cases import (
    CancelSubscription,
    GetOrCreateSubscription,
    StartCheckout,
    StartPortal,
)
from src.billing.domain.entities import PLAN_LIMITS, Plan
from src.billing.infrastructure.payments import MockStripeProvider
from src.billing.infrastructure.repositories import SqlAlchemySubscriptionRepository
from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.shared.config import get_settings
from src.shared.uow import unit_of_work

router = APIRouter()


@router.get("/plans")
async def list_plans() -> dict[str, Any]:
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "price_eur_month": 0,
                "limits": PLAN_LIMITS["free"].__dict__,
            },
            {
                "id": "premium",
                "name": "Premium",
                "price_eur_month": 9.99,
                "price_eur_year": 89,
                "limits": PLAN_LIMITS["premium"].__dict__,
            },
            {
                "id": "pro",
                "name": "Pro",
                "price_eur_month": 19.99,
                "price_eur_year": 179,
                "limits": PLAN_LIMITS["pro"].__dict__,
            },
        ]
    }


@router.get("/subscription")
async def get_subscription(user_id: CurrentUserId, session: SessionDep) -> dict[str, Any]:
    from uuid import UUID

    uc = GetOrCreateSubscription(SqlAlchemySubscriptionRepository(session))
    sub = await uc.execute(UUID(user_id))
    return {
        "plan": sub.plan,
        "status": sub.status,
        "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "limits": sub.limits.__dict__,
    }


class CheckoutRequest(BaseModel):
    plan: Literal["premium", "pro"]
    return_url: str | None = None


@router.post("/checkout")
async def create_checkout(
    user_id: CurrentUserId,
    body: CheckoutRequest,
    session: SessionDep,
) -> dict[str, str]:
    settings = get_settings()
    uc = StartCheckout(MockStripeProvider(session))
    url = await uc.execute(
        user_id=user_id,
        plan=body.plan,
        return_url=body.return_url or f"{settings.frontend_base_url}/settings/billing",
    )
    return {"checkout_url": url}


@router.post("/portal")
async def create_portal(
    user_id: CurrentUserId,
    session: SessionDep,
    body: dict[str, str] = Body(default_factory=dict),
) -> dict[str, str]:
    settings = get_settings()
    uc = StartPortal(MockStripeProvider(session))
    url = await uc.execute(
        user_id=user_id,
        return_url=body.get("return_url") or f"{settings.frontend_base_url}/settings/billing",
    )
    return {"portal_url": url}


@router.post("/cancel")
async def cancel_subscription(
    user_id: CurrentUserId, session: SessionDep
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        uc = CancelSubscription(
            SqlAlchemySubscriptionRepository(session),
            MockStripeProvider(session),
        )
        r = await uc.execute(user_id=user_id)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()
        sub = r.value  # type: ignore[union-attr]
    return {"plan": sub.plan, "status": sub.status}


class WebhookTestRequest(BaseModel):
    event: Literal["checkout.completed", "subscription.canceled"]
    user_id: str
    plan: Plan | None = None


@router.post("/webhook/test")
async def webhook_test(
    body: WebhookTestRequest,
    session: SessionDep,
) -> dict[str, Any]:
    """MOCK-ONLY webhook to simulate Stripe events from the frontend."""
    from uuid import UUID

    payments = MockStripeProvider(session)
    async with unit_of_work(session) as uow:
        if body.event == "checkout.completed":
            sub = await payments.simulate_checkout_success(
                user_id=UUID(body.user_id), plan=body.plan or "premium"
            )
            await uow.commit()
            return {"plan": sub.plan, "status": sub.status}
        # canceled
        from src.billing.infrastructure.repositories import SqlAlchemySubscriptionRepository

        subs = SqlAlchemySubscriptionRepository(session)
        sub = await subs.get(UUID(body.user_id))
        if sub is None:
            return {"plan": "free", "status": "active"}
        sub.plan = "free"
        sub.status = "canceled"
        from src.shared.security import utc_now

        sub.updated_at = utc_now()
        await subs.upsert(sub)
        await uow.commit()
        return {"plan": sub.plan, "status": sub.status}
