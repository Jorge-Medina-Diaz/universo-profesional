"""Real Stripe provider — checkout sessions, customer portal, webhook HMAC.

We talk to Stripe's REST API directly with httpx rather than pulling the
Stripe SDK. The SDK is heavy (~5 MB of generated code) and we use very few
endpoints. Direct httpx keeps the dep surface small and the code obvious.

Endpoints used:
  * POST /v1/customers              — create-or-reuse a customer per user
  * POST /v1/checkout/sessions      — Stripe Checkout (hosted)
  * POST /v1/billing_portal/sessions — Customer Portal (cancel, swap card)
  * POST /v1/subscriptions/{id}     — used on cancel for at-period-end

Webhook handling lives in `router.py`; the HMAC verifier helper here is
shared so future webhook routes (e.g. invoice.paid notifications) can
reuse it.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.application.ports import PaymentsProvider
from src.billing.infrastructure.repositories import SqlAlchemySubscriptionRepository
from src.shared.config import get_settings

logger = structlog.get_logger(__name__)


STRIPE_API_BASE = "https://api.stripe.com"
STRIPE_API_VERSION = "2024-12-18.acacia"


class StripeError(Exception):
    """Raised when Stripe returns 4xx/5xx or signature verification fails."""

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"Stripe error {status_code}: {body[:200]}")
        self.status_code = status_code


class StripeProvider(PaymentsProvider):
    """Production-ready Stripe client.

    Caches the per-user `stripe_customer_id` in our `subscriptions` table to
    avoid creating a new customer on every checkout. The customer email is
    sourced from the user record; we pass `customer_email` to the checkout
    session as a fallback when we don't have a customer id yet.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._subs = SqlAlchemySubscriptionRepository(session)
        s = get_settings()
        if not s.stripe_api_key:
            raise StripeError(
                500, "STRIPE_API_KEY not configured — cannot use real provider"
            )
        self._api_key = s.stripe_api_key
        self._webhook_secret = s.stripe_webhook_secret
        self._price_premium = s.stripe_price_premium_monthly
        self._price_pro = s.stripe_price_pro_monthly
        self._success_url = s.stripe_success_url
        self._cancel_url = s.stripe_cancel_url
        self._http = httpx.AsyncClient(timeout=15.0)

    async def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        # Stripe expects application/x-www-form-urlencoded with array
        # notation for nested fields. httpx encodes dicts of strings as
        # form-urlencoded automatically.
        resp = await self._http.post(
            f"{STRIPE_API_BASE}{path}",
            data=_flatten_form(data),
            auth=(self._api_key, ""),
            headers={"Stripe-Version": STRIPE_API_VERSION},
        )
        if resp.status_code >= 400:
            raise StripeError(resp.status_code, resp.text)
        return resp.json()

    async def _ensure_customer(self, *, user_id: UUID, email: str | None) -> str:
        sub = await self._subs.get(user_id)
        if sub and sub.stripe_customer_id:
            return sub.stripe_customer_id

        payload: dict[str, Any] = {"metadata[user_id]": str(user_id)}
        if email:
            payload["email"] = email
        result = await self._post("/v1/customers", payload)
        customer_id = str(result["id"])

        # Persist on the subscription row so next call reuses it.
        if sub:
            sub.stripe_customer_id = customer_id
            from src.shared.security import utc_now

            sub.updated_at = utc_now()
            await self._subs.upsert(sub)
        return customer_id

    def _price_for_plan(self, plan: str) -> str:
        if plan == "premium":
            if not self._price_premium:
                raise StripeError(500, "STRIPE_PRICE_PREMIUM_MONTHLY not configured")
            return self._price_premium
        if plan == "pro":
            if not self._price_pro:
                raise StripeError(500, "STRIPE_PRICE_PRO_MONTHLY not configured")
            return self._price_pro
        raise StripeError(400, f"unknown plan: {plan}")

    async def create_checkout(
        self, *, user_id: UUID, plan: str, return_url: str
    ) -> str:
        # Try to enrich with email (helps Stripe match an existing customer).
        from src.identity.infrastructure.repositories import SqlAlchemyUserRepository

        users = SqlAlchemyUserRepository(self._session)
        user = await users.get_by_id(user_id)
        email = str(user.email) if user else None
        customer_id = await self._ensure_customer(user_id=user_id, email=email)

        success_url = self._success_url or return_url
        cancel_url = self._cancel_url or return_url
        result = await self._post(
            "/v1/checkout/sessions",
            {
                "mode": "subscription",
                "customer": customer_id,
                "success_url": success_url,
                "cancel_url": cancel_url,
                "client_reference_id": str(user_id),
                "metadata[user_id]": str(user_id),
                "metadata[plan]": plan,
                "line_items[0][price]": self._price_for_plan(plan),
                "line_items[0][quantity]": "1",
                "subscription_data[metadata][user_id]": str(user_id),
                "subscription_data[metadata][plan]": plan,
                "allow_promotion_codes": "true",
            },
        )
        return str(result["url"])

    async def create_portal(self, *, user_id: UUID, return_url: str) -> str:
        sub = await self._subs.get(user_id)
        if not sub or not sub.stripe_customer_id:
            raise StripeError(404, "no Stripe customer for this user")
        result = await self._post(
            "/v1/billing_portal/sessions",
            {
                "customer": sub.stripe_customer_id,
                "return_url": return_url,
            },
        )
        return str(result["url"])

    async def cancel(self, *, user_id: UUID) -> None:
        sub = await self._subs.get(user_id)
        if not sub or not sub.stripe_subscription_id:
            return
        # Cancel at period end (no proration). The user keeps access until
        # the current billing cycle ends; our webhook handler will downgrade
        # them to free on `customer.subscription.deleted`.
        await self._post(
            f"/v1/subscriptions/{sub.stripe_subscription_id}",
            {"cancel_at_period_end": "true"},
        )


# --- Webhook signature verification --------------------------------------


_DEFAULT_TOLERANCE_SECONDS = 300  # 5 minutes per Stripe recommendation


def verify_stripe_signature(
    payload: bytes,
    sig_header: str,
    secret: str,
    *,
    tolerance: int = _DEFAULT_TOLERANCE_SECONDS,
    now: float | None = None,
) -> bool:
    """Verify the `Stripe-Signature` header per Stripe docs.

    Header format: `t=1605142399,v1=abc...,v0=def...`. We compute
    `HMAC_SHA256(secret, f"{t}.{payload}")` and compare to v1.

    Returns True on valid signature within tolerance, False otherwise. Never
    raises — callers should respond 400 to invalid webhooks.
    """
    if not sig_header or not secret:
        return False
    parts: dict[str, list[str]] = {}
    for item in sig_header.split(","):
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        parts.setdefault(k.strip(), []).append(v.strip())
    timestamp_strs = parts.get("t", [])
    sigs = parts.get("v1", [])
    if not timestamp_strs or not sigs:
        return False
    try:
        timestamp = int(timestamp_strs[0])
    except ValueError:
        return False
    current = now if now is not None else time.time()
    if abs(current - timestamp) > tolerance:
        return False
    signed_payload = f"{timestamp}.{payload.decode('utf-8', errors='replace')}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, s) for s in sigs)


def _flatten_form(payload: dict[str, Any]) -> dict[str, str]:
    """Coerce values to strings for httpx form encoding.

    Stripe expects bare strings even for `true`/`1` literals — booleans and
    numbers go through `str()`. None values are dropped so optional fields
    don't get serialized as the literal string "None".
    """
    out: dict[str, str] = {}
    for k, v in payload.items():
        if v is None:
            continue
        if isinstance(v, bool):
            out[k] = "true" if v else "false"
        else:
            out[k] = str(v)
    return out
