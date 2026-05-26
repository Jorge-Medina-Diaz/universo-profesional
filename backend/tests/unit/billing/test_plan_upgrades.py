"""Unit tests: billing plan upgrades / downgrades."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from src.billing.application.use_cases import CancelSubscription
from src.billing.domain.entities import Subscription
from src.shared.errors import NotFoundError


class FakePaymentsProvider:
    def __init__(self) -> None:
        self.canceled = []

    async def create_checkout(self, *, user_id, plan, return_url):
        return "https://checkout.test"

    async def create_portal(self, *, user_id, return_url):
        return "https://portal.test"

    async def cancel(self, *, user_id):
        self.canceled.append(user_id)


class FakeSubscriptionRepository:
    def __init__(self, sub: Subscription | None = None) -> None:
        self._sub = sub

    async def get(self, user_id):
        return self._sub

    async def upsert(self, subscription):
        self._sub = subscription


@pytest.mark.asyncio
async def test_cancel_existing_subscription() -> None:
    uid = uuid4()
    now = datetime.now(UTC)
    sub = Subscription(
        user_id=uid,
        plan="premium",
        status="active",
        stripe_customer_id="cus_123",
        stripe_subscription_id="sub_123",
        trial_ends_at=None,
        current_period_start=now,
        current_period_end=now,
        cancel_at=None,
        created_at=now,
        updated_at=now,
    )
    repo = FakeSubscriptionRepository(sub)
    payments = FakePaymentsProvider()
    uc = CancelSubscription(repo, payments)

    result = await uc.execute(user_id=str(uid))
    assert result.is_success
    assert result.value.plan == "free"
    assert result.value.status == "canceled"
    assert uid in payments.canceled


@pytest.mark.asyncio
async def test_cancel_missing_subscription_fails() -> None:
    uid = uuid4()
    repo = FakeSubscriptionRepository(None)
    payments = FakePaymentsProvider()
    uc = CancelSubscription(repo, payments)

    result = await uc.execute(user_id=str(uid))
    assert result.is_failure
    assert isinstance(result.error, NotFoundError)


class TestSubscriptionEntity:
    def test_free_for_creates_active_free(self) -> None:
        uid = uuid4()
        now = datetime.now(UTC)
        sub = Subscription.free_for(uid, now)
        assert sub.plan == "free"
        assert sub.status == "active"
        assert sub.stripe_customer_id is None

    def test_is_active_for_active(self) -> None:
        uid = uuid4()
        now = datetime.now(UTC)
        sub = Subscription.free_for(uid, now)
        assert sub.is_active is True

    def test_is_paying_for_free(self) -> None:
        uid = uuid4()
        now = datetime.now(UTC)
        sub = Subscription.free_for(uid, now)
        assert sub.is_paying is False

    def test_is_paying_for_premium_active(self) -> None:
        uid = uuid4()
        now = datetime.now(UTC)
        sub = Subscription(
            user_id=uid,
            plan="premium",
            status="active",
            stripe_customer_id=None,
            stripe_subscription_id=None,
            trial_ends_at=None,
            current_period_start=now,
            current_period_end=None,
            cancel_at=None,
            created_at=now,
            updated_at=now,
        )
        assert sub.is_paying is True

    def test_limits_match_plan(self) -> None:
        uid = uuid4()
        now = datetime.now(UTC)
        sub = Subscription.free_for(uid, now)
        assert sub.limits.monthly_cv == 3
