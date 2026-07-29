"""Stripe-like payments provider — mock + factory for the real one.

The factory `get_payments_provider(session)` picks between the mock and
the real Stripe provider based on `settings.stripe_provider`. Callers don't
need to know which one they got — both implement `PaymentsProvider`.
"""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.application.ports import PaymentsProvider
from src.billing.domain.entities import Plan, Subscription
from src.billing.infrastructure.repositories import SqlAlchemySubscriptionRepository
from src.shared.config import get_settings
from src.shared.security import utc_in, utc_now

logger = structlog.get_logger(__name__)


def get_payments_provider(session: AsyncSession) -> PaymentsProvider:
    """Return the configured Stripe provider.

    Real provider requires STRIPE_API_KEY; if `stripe_provider=real` but the
    key is missing we explicitly fall back to mock (with a warning) so dev
    work doesn't break when someone half-configures Stripe.
    """
    settings = get_settings()
    if settings.stripe_provider == "real" and settings.stripe_api_key:
        from src.billing.infrastructure.stripe_provider import StripeProvider

        return StripeProvider(session)
    if settings.stripe_provider == "real":
        logger.warning("stripe_real_no_key", message="falling back to mock")
    return MockStripeProvider(session)


class MockStripeProvider(PaymentsProvider):
    """Emulates Stripe Checkout + Customer Portal without external calls.

    `create_checkout` returns a frontend URL `/billing/checkout-mock?plan=&user=`
    that the SPA renders into a "click to confirm" page; the SPA then POSTs
    to `/api/v1/billing/webhook/test` which `MockStripeProvider` consumes
    to upgrade the user.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._subs = SqlAlchemySubscriptionRepository(session)

    async def create_checkout(self, *, user_id: UUID, plan: str, return_url: str) -> str:
        s = get_settings()
        return (
            f"{s.frontend_base_url}/billing/checkout-mock"
            f"?plan={plan}&user_id={user_id}&return_url={return_url}"
        )

    async def create_portal(self, *, user_id: UUID, return_url: str) -> str:
        s = get_settings()
        return f"{s.frontend_base_url}/billing/portal-mock?user_id={user_id}&return_url={return_url}"

    async def cancel(self, *, user_id: UUID) -> None:
        # No external call; the use case downgrades the local subscription
        logger.info("mock_stripe_cancel", user_id=str(user_id))

    async def simulate_checkout_success(
        self, *, user_id: UUID, plan: Plan
    ) -> Subscription:
        now = utc_now()
        sub = await self._subs.get(user_id) or Subscription.free_for(user_id, now)
        sub.plan = plan
        sub.status = "active"
        sub.stripe_customer_id = f"cus_mock_{user_id}"
        sub.stripe_subscription_id = f"sub_mock_{user_id}"
        sub.current_period_start = now
        sub.current_period_end = utc_in(days=30)
        sub.cancel_at = None
        sub.updated_at = now
        await self._subs.upsert(sub)
        return sub
