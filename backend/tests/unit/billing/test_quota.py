"""Unit tests: billing quota enforcement."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.billing.application.use_cases import CheckQuota
from src.billing.domain.entities import PLAN_LIMITS, PlanLimits, Subscription
from src.shared.errors import QuotaExceededError
from src.shared.result import Result


class FakeSubscriptionRepository:
    def __init__(self, sub: Subscription | None) -> None:
        self._sub = sub

    async def get(self, user_id):  # noqa: ANN001,ANN202
        return self._sub

    async def upsert(self, subscription):  # noqa: ANN001,ANN202
        self._sub = subscription


class FakeQuotaRepository:
    def __init__(self, counter: int = 0) -> None:
        self._counter = counter

    async def increment(self, user_id, resource, period):  # noqa: ANN001,ANN202
        self._counter += 1
        return self._counter

    async def current(self, user_id, resource, period):  # noqa: ANN001,ANN202
        return self._counter


@pytest.mark.asyncio
async def test_free_plan_cv_quota_enforced() -> None:
    uid = uuid4()
    sub = Subscription.free_for(uid, datetime.now(timezone.utc))
    uc = CheckQuota(FakeSubscriptionRepository(sub), FakeQuotaRepository(counter=3))
    result = await uc.execute(user_id=str(uid), resource="cv_generated")
    assert result.is_failure
    assert isinstance(result.error, QuotaExceededError)


@pytest.mark.asyncio
async def test_free_plan_cv_under_quota_allowed() -> None:
    uid = uuid4()
    sub = Subscription.free_for(uid, datetime.now(timezone.utc))
    uc = CheckQuota(FakeSubscriptionRepository(sub), FakeQuotaRepository(counter=2))
    result = await uc.execute(user_id=str(uid), resource="cv_generated")
    assert result.is_success


@pytest.mark.asyncio
async def test_premium_plan_unlimited_cv() -> None:
    uid = uuid4()
    now = datetime.now(timezone.utc)
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
    uc = CheckQuota(FakeSubscriptionRepository(sub), FakeQuotaRepository(counter=9999))
    result = await uc.execute(user_id=str(uid), resource="cv_generated")
    assert result.is_success


@pytest.mark.asyncio
async def test_mcp_access_denied_for_free() -> None:
    uid = uuid4()
    sub = Subscription.free_for(uid, datetime.now(timezone.utc))
    uc = CheckQuota(FakeSubscriptionRepository(sub), FakeQuotaRepository())
    result = await uc.execute(user_id=str(uid), resource="mcp_call")
    assert result.is_failure
    assert isinstance(result.error, QuotaExceededError)
    assert "MCP access requires Premium" in str(result.error)


@pytest.mark.asyncio
async def test_mcp_allowed_for_pro_within_limit() -> None:
    uid = uuid4()
    now = datetime.now(timezone.utc)
    sub = Subscription(
        user_id=uid,
        plan="pro",
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
    uc = CheckQuota(FakeSubscriptionRepository(sub), FakeQuotaRepository(counter=500))
    result = await uc.execute(user_id=str(uid), resource="mcp_call")
    assert result.is_success


@pytest.mark.asyncio
async def test_unknown_resource_allowed() -> None:
    uid = uuid4()
    sub = Subscription.free_for(uid, datetime.now(timezone.utc))
    uc = CheckQuota(FakeSubscriptionRepository(sub), FakeQuotaRepository())
    result = await uc.execute(user_id=str(uid), resource="unknown_thing")
    assert result.is_success


class TestPlanLimits:
    def test_free_limits(self) -> None:
        limits = PLAN_LIMITS["free"]
        assert limits.monthly_cv == 3
        assert limits.monthly_cover_letters == 1
        assert limits.mcp_access is False

    def test_premium_limits(self) -> None:
        limits = PLAN_LIMITS["premium"]
        assert limits.monthly_cv == -1
        assert limits.mcp_access is True

    def test_pro_limits(self) -> None:
        limits = PLAN_LIMITS["pro"]
        assert limits.mcp_daily_calls == 1000
