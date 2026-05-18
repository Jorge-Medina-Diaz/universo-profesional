"""Billing repositories."""
from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.application.ports import QuotaRepository, SubscriptionRepository
from src.billing.domain.entities import Plan, Subscription, SubscriptionStatus
from src.billing.infrastructure.orm import SubscriptionOrm
from src.shared.security import utc_now


class SqlAlchemySubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> Subscription | None:
        row = await self._session.get(SubscriptionOrm, user_id)
        if row is None:
            return None
        return Subscription(
            user_id=row.user_id,
            plan=cast(Plan, row.plan),
            status=cast(SubscriptionStatus, row.status),
            stripe_customer_id=row.stripe_customer_id,
            stripe_subscription_id=row.stripe_subscription_id,
            trial_ends_at=row.trial_ends_at,
            current_period_start=row.current_period_start,
            current_period_end=row.current_period_end,
            cancel_at=row.cancel_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def upsert(self, subscription: Subscription) -> None:
        existing = await self._session.get(SubscriptionOrm, subscription.user_id)
        if existing is None:
            self._session.add(
                SubscriptionOrm(
                    user_id=subscription.user_id,
                    plan=subscription.plan,
                    status=subscription.status,
                    stripe_customer_id=subscription.stripe_customer_id,
                    stripe_subscription_id=subscription.stripe_subscription_id,
                    trial_ends_at=subscription.trial_ends_at,
                    current_period_start=subscription.current_period_start,
                    current_period_end=subscription.current_period_end,
                    cancel_at=subscription.cancel_at,
                    created_at=subscription.created_at,
                    updated_at=subscription.updated_at,
                )
            )
        else:
            existing.plan = subscription.plan
            existing.status = subscription.status
            existing.stripe_customer_id = subscription.stripe_customer_id
            existing.stripe_subscription_id = subscription.stripe_subscription_id
            existing.trial_ends_at = subscription.trial_ends_at
            existing.current_period_start = subscription.current_period_start
            existing.current_period_end = subscription.current_period_end
            existing.cancel_at = subscription.cancel_at
            existing.updated_at = subscription.updated_at
        await self._session.flush()


class SqlAlchemyQuotaRepository(QuotaRepository):
    """Counter table; uses INSERT ... ON CONFLICT for atomic-ish increments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def increment(self, user_id: UUID, resource: str, period: str) -> int:
        stmt = text(
            """
            INSERT INTO quota_usage (user_id, resource, period, counter, updated_at)
            VALUES (:uid, :res, :p, 1, :now)
            ON CONFLICT (user_id, resource, period)
            DO UPDATE SET counter = quota_usage.counter + 1, updated_at = :now
            RETURNING counter
            """
        )
        result = await self._session.execute(
            stmt,
            {"uid": str(user_id), "res": resource, "p": period, "now": utc_now()},
        )
        row = result.first()
        return int(row[0]) if row else 0

    async def current(self, user_id: UUID, resource: str, period: str) -> int:
        stmt = text(
            "SELECT counter FROM quota_usage "
            "WHERE user_id = :uid AND resource = :res AND period = :p"
        )
        result = await self._session.execute(
            stmt, {"uid": str(user_id), "res": resource, "p": period}
        )
        row = result.first()
        return int(row[0]) if row else 0
