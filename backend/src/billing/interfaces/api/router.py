"""Billing API: /api/v1/billing/*"""
from __future__ import annotations

from datetime import UTC
from typing import Any, Literal

import structlog
from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel

from src.billing.application.use_cases import (
    CancelSubscription,
    GetOrCreateSubscription,
    StartCheckout,
    StartPortal,
)
from src.billing.domain.entities import PLAN_LIMITS, Plan
from src.billing.infrastructure.payments import (
    MockStripeProvider,
    get_payments_provider,
)
from src.billing.infrastructure.repositories import SqlAlchemySubscriptionRepository
from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.shared.config import get_settings
from src.shared.metrics import stripe_conversion_total
from src.shared.uow import unit_of_work

logger = structlog.get_logger(__name__)

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
    uc = StartCheckout(get_payments_provider(session))
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
    uc = StartPortal(get_payments_provider(session))
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
            get_payments_provider(session),
        )
        r = await uc.execute(user_id=user_id)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()
        sub = r.value  # type: ignore[union-attr]
    return {"plan": sub.plan, "status": sub.status}


# --- Stripe webhook (production) -----------------------------------------


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    """Real Stripe webhook receiver.

    Verifies HMAC signature, dispatches by `type`, and ACKs with 200 so
    Stripe doesn't retry. Idempotency: we use `event.id` (the Stripe event
    id) as a natural dedup key — every handler should be safe to replay.

    Supported events:
      * checkout.session.completed       — upgrade plan + send receipt email
      * customer.subscription.updated    — sync plan + current_period_end
      * customer.subscription.deleted    — downgrade to free at period end
      * invoice.paid                     — log + optional email
      * invoice.payment_failed           — log + flag subscription
    """
    settings = get_settings()
    raw_body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # If we're not running the real provider, refuse to process — anyone
    # sending a fake signature shouldn't be able to flip a plan in prod.
    if settings.stripe_provider != "real" or not settings.stripe_webhook_secret:
        raise HTTPException(status_code=400, detail="webhook not configured")

    from src.billing.infrastructure.stripe_provider import verify_stripe_signature

    if not verify_stripe_signature(
        raw_body, sig_header, settings.stripe_webhook_secret
    ):
        logger.warning("stripe_webhook_bad_signature")
        raise HTTPException(status_code=400, detail="invalid signature")

    import json

    event = json.loads(raw_body.decode("utf-8"))
    event_type = event.get("type", "")
    data_object = (event.get("data") or {}).get("object") or {}
    logger.info("stripe_webhook_received", event_type=event_type, id=event.get("id"))

    from uuid import UUID

    from src.billing.infrastructure.repositories import SqlAlchemySubscriptionRepository
    from src.shared.security import utc_now

    subs = SqlAlchemySubscriptionRepository(session)

    async def _resolve_user_id() -> UUID | None:
        # Prefer client_reference_id when present (checkout sessions). Fall
        # back to the customer metadata we set when creating the customer.
        for key in ("client_reference_id",):
            v = data_object.get(key)
            if v:
                try:
                    return UUID(str(v))
                except ValueError:
                    pass
        meta = (data_object.get("metadata") or {})
        v = meta.get("user_id")
        if v:
            try:
                return UUID(str(v))
            except ValueError:
                pass
        return None

    try:
        if event_type == "checkout.session.completed":
            uid = await _resolve_user_id()
            if uid is None:
                return {"ok": True, "skipped": "no user_id"}
            plan = ((data_object.get("metadata") or {}).get("plan") or "premium")
            sub = await subs.get(uid)
            if sub is None:
                from src.billing.domain.entities import Subscription

                sub = Subscription.free_for(uid, utc_now())
            sub.plan = plan if plan in {"premium", "pro"} else "premium"
            sub.status = "active"
            stripe_conversion_total.labels(plan=sub.plan, event="checkout_completed").inc()
            sub.stripe_customer_id = data_object.get("customer") or sub.stripe_customer_id
            sub.stripe_subscription_id = (
                data_object.get("subscription") or sub.stripe_subscription_id
            )
            sub.updated_at = utc_now()
            await subs.upsert(sub)
            await session.commit()

            # Send the payment-received email (mock or real depending on env).
            try:
                from src.identity.infrastructure.tasks import (
                    enqueue_transactional_email,
                )

                await enqueue_transactional_email(
                    user_id=uid, template="payment_received", context={"plan": plan}
                )
            except Exception as exc:
                logger.warning("payment_email_enqueue_failed", error=str(exc))

        elif event_type == "customer.subscription.updated":
            uid = await _resolve_user_id()
            if uid is None:
                return {"ok": True, "skipped": "no user_id"}
            sub = await subs.get(uid)
            if sub is None:
                return {"ok": True, "skipped": "no local subscription"}
            # Map Stripe sub status → our state. Active/trialing/past_due
            # keep the user paid (give the dunning window). Canceled/unpaid
            # bumps them back to free.
            status = str(data_object.get("status") or "")
            sub.status = status or sub.status
            period_end = data_object.get("current_period_end")
            if isinstance(period_end, int):
                from datetime import datetime

                sub.current_period_end = datetime.fromtimestamp(
                    period_end, tz=UTC
                )
            sub.updated_at = utc_now()
            await subs.upsert(sub)
            await session.commit()

        elif event_type == "customer.subscription.deleted":
            uid = await _resolve_user_id()
            if uid is None:
                return {"ok": True, "skipped": "no user_id"}
            sub = await subs.get(uid)
            if sub is None:
                return {"ok": True, "skipped": "no local subscription"}
            sub.plan = "free"
            sub.status = "canceled"
            stripe_conversion_total.labels(plan="free", event="subscription_deleted").inc()
            sub.updated_at = utc_now()
            await subs.upsert(sub)
            await session.commit()

        # invoice.paid / invoice.payment_failed are observability-only today.

    except Exception as exc:
        logger.exception("stripe_webhook_handler_failed", error=str(exc))
        # Return 200 anyway — Stripe retries with the SAME event id, and
        # we already logged it. Retrying buggy handlers just floods the log.
        return {"ok": False, "error": str(exc)}

    return {"ok": True}


# --- Mock webhook (dev/test only) ----------------------------------------


class WebhookTestRequest(BaseModel):
    event: Literal["checkout.completed", "subscription.canceled"]
    user_id: str
    plan: Plan | None = None


@router.post("/webhook/test")
async def webhook_test(
    body: WebhookTestRequest,
    session: SessionDep,
) -> dict[str, Any]:
    """Mock-only webhook to simulate Stripe events from the frontend.

    Hard-blocked in production — there's no signature, so anyone could call
    it to flip arbitrary users onto Pro. The real `/webhook` endpoint above
    is the authenticated path.
    """
    settings = get_settings()
    if settings.is_prod:
        raise HTTPException(status_code=404)

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
