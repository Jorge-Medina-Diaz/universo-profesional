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
from src.billing.infrastructure.repositories import (
    SqlAlchemyQuotaRepository,
    SqlAlchemySubscriptionRepository,
)
from src.identity.interfaces.api.deps import (
    CurrentUserId,
    ServiceSessionDep,
    SessionDep,
)
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


@router.get("/usage")
async def get_usage(user_id: CurrentUserId, session: SessionDep) -> dict[str, Any]:
    """Current-period quota usage per metered resource (PENDING: MCP quota
    visibility). `limit` of 0/None means the resource is not available on the
    plan; the FE warns at >=80%."""
    from uuid import UUID

    from src.billing.application.use_cases import _period_key
    from src.shared.security import utc_now

    uid = UUID(user_id)
    sub = await GetOrCreateSubscription(
        SqlAlchemySubscriptionRepository(session)
    ).execute(uid)
    quotas = SqlAlchemyQuotaRepository(session)
    limits = sub.limits
    resources = {
        "mcp_call": (limits.mcp_daily_calls if limits.mcp_access else 0, "day"),
        "cv_generated": (limits.monthly_cv, "month"),
        "cover_letter_generated": (limits.monthly_cover_letters, "month"),
    }
    now = utc_now()
    usage = []
    for resource, (cap, window) in resources.items():
        used = await quotas.current(uid, resource, _period_key(resource, now))
        usage.append(
            {
                "resource": resource,
                "used": used,
                "limit": cap,
                "window": window,
                "remaining": max(0, cap - used) if cap else 0,
            }
        )
    return {"plan": sub.plan, "usage": usage}


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
            raise r.error
        await uow.commit()
        sub = r.value
    return {"plan": sub.plan, "status": sub.status}


def _plan_from_subscription_object(data_object: dict[str, Any], settings: Any) -> str | None:
    """Derive our plan from a Stripe subscription object.

    Prefers the active price id (portal-initiated plan changes alter the price,
    not just the status), then falls back to the metadata we set at checkout.
    Returns None when it can't be determined (caller keeps the current plan).
    """
    try:
        items = ((data_object.get("items") or {}).get("data")) or []
        price_id = items[0].get("price", {}).get("id") if items else None
    except (AttributeError, IndexError, TypeError):
        price_id = None
    if price_id:
        if price_id == settings.stripe_price_pro_monthly:
            return "pro"
        if price_id == settings.stripe_price_premium_monthly:
            return "premium"
    meta_plan = (data_object.get("metadata") or {}).get("plan")
    if meta_plan in {"premium", "pro"}:
        return meta_plan
    return None


# --- Stripe webhook (production) -----------------------------------------


@router.post("/webhook")
async def stripe_webhook(  # noqa: PLR0912, PLR0915 - Stripe webhook: one branch per event type, splitting it would only hide the fan-out
    request: Request,
    session: ServiceSessionDep,
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
    event_id = event.get("id")
    data_object = (event.get("data") or {}).get("object") or {}
    logger.info("stripe_webhook_received", event_type=event_type, id=event_id)

    from uuid import UUID

    from sqlalchemy import text as _sql_text

    from src.billing.infrastructure.repositories import (
        SqlAlchemySubscriptionRepository,
    )
    from src.shared.security import utc_now

    # Idempotency: Stripe retries delivery on any non-2xx/timeout with the SAME
    # event id, so a previously-processed event must be a no-op (don't upgrade
    # a user twice or re-send the receipt). See migration 0028.
    if event_id:
        seen = await session.execute(
            _sql_text("SELECT 1 FROM stripe_processed_events WHERE event_id = :eid"),
            {"eid": event_id},
        )
        if seen.first() is not None:
            logger.info("stripe_webhook_duplicate", id=event_id, event_type=event_type)
            return {"ok": True, "duplicate": True}

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
        # Invoice events carry only `customer` — map it to our local row.
        customer = data_object.get("customer")
        if customer:
            row = await session.execute(
                _sql_text(
                    "SELECT user_id FROM subscriptions WHERE stripe_customer_id = :cust LIMIT 1"
                ),
                {"cust": str(customer)},
            )
            found = row.scalar_one_or_none()
            if found is not None:
                try:
                    return UUID(str(found))
                except ValueError:
                    pass
        return None

    async def _sync_user_tier(uid: UUID, sub: Any) -> None:
        """Mirror the subscription's effective plan onto users.tier — the single
        denormalized field every entitlement gate reads. Without this the
        webhook updated subscriptions.plan but users.tier stayed 'free', so paid
        users were locked out of paid features. Goes through the domain so the
        TierChanged event + tier_updated_at fire."""
        from src.identity.infrastructure.repositories import (
            SqlAlchemyUserRepository,
        )

        target_tier = sub.plan if sub.is_paying else "free"
        user_repo = SqlAlchemyUserRepository(session)
        user = await user_repo.get_by_id(uid)
        if user is None or user.is_deleted:
            return
        if user.tier == target_tier:
            return
        user.set_tier(target_tier, now=utc_now())
        await user_repo.save(user)

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
            await _sync_user_tier(uid, sub)
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
            # Portal-initiated upgrades/downgrades change the price, not just
            # the status — keep our plan in sync too.
            new_plan = _plan_from_subscription_object(data_object, settings)
            if new_plan:
                sub.plan = new_plan
            period_end = data_object.get("current_period_end")
            if isinstance(period_end, int):
                from datetime import datetime

                sub.current_period_end = datetime.fromtimestamp(
                    period_end, tz=UTC
                )
            sub.updated_at = utc_now()
            await subs.upsert(sub)
            await _sync_user_tier(uid, sub)
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
            await _sync_user_tier(uid, sub)
            await session.commit()

        elif event_type == "invoice.payment_failed":
            uid = await _resolve_user_id()
            if uid is None:
                return {"ok": True, "skipped": "no user_id"}
            sub = await subs.get(uid)
            if sub is not None and sub.status != "canceled":
                sub.status = "past_due"
                sub.updated_at = utc_now()
                await subs.upsert(sub)
                await session.commit()
                stripe_conversion_total.labels(
                    plan=sub.plan, event="payment_failed"
                ).inc()

        elif event_type == "invoice.paid":
            # A successful payment after a failure clears the dunning state.
            uid = await _resolve_user_id()
            if uid is None:
                return {"ok": True, "skipped": "no user_id"}
            sub = await subs.get(uid)
            if sub is not None and sub.status == "past_due":
                sub.status = "active"
                sub.updated_at = utc_now()
                await subs.upsert(sub)
                await session.commit()

    except Exception as exc:
        logger.exception("stripe_webhook_handler_failed", id=event_id, error=str(exc))
        # Do NOT mark the event processed; signal failure so Stripe retries with
        # the same id (the idempotency guard above makes replays safe).
        raise HTTPException(status_code=500, detail="webhook handler failed") from exc

    # Mark processed only after a successful handler run.
    if event_id:
        await session.execute(
            _sql_text(
                "INSERT INTO stripe_processed_events (event_id, event_type) "
                "VALUES (:eid, :etype) ON CONFLICT (event_id) DO NOTHING"
            ),
            {"eid": event_id, "etype": event_type},
        )
        await session.commit()

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
    # Local dev/test only — never staging or prod. There's no signature here,
    # so anyone could call it to flip arbitrary users onto Pro.
    if settings.env not in ("development", "test"):
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
