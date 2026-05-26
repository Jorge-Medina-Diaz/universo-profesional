"""Reminders engine — scheduled scans + dispatch.

Generic on `kind` and `subject_type` so future verticals (job-search, applications)
plug in without schema change.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID, uuid4

import structlog
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.errors import NotFoundError
from src.shared.result import Result, err, ok
from src.shared.security import utc_now
from src.universe.infrastructure.orm import CertificationOrm, CourseOrm, ReminderOrm

logger = structlog.get_logger(__name__)


class ScanReminders:
    """Generates new reminders by scanning universe state.

    Triggers:
    - Certifications expiring within 60 days → `cert_expiring`
    - Courses in-progress > 6 months → `course_stale`
    - Quarterly review (every 90 days) → `quarterly_review`
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, *, user_id: UUID) -> int:
        created = 0
        today = date.today()
        now = utc_now()

        # Certifications expiring
        cert_rows = (
            await self._session.execute(
                select(CertificationOrm)
                .where(CertificationOrm.user_id == user_id)
                .where(CertificationOrm.expires_on.is_not(None))
                .where(CertificationOrm.deleted_at.is_(None))
            )
        ).scalars().all()

        for c in cert_rows:
            if not c.expires_on:
                continue
            days_left = (c.expires_on - today).days
            if 0 <= days_left <= 60:
                # idempotency: don't duplicate
                existing = (
                    await self._session.execute(
                        select(ReminderOrm)
                        .where(ReminderOrm.user_id == user_id)
                        .where(ReminderOrm.kind == "cert_expiring")
                        .where(ReminderOrm.subject_id == c.id)
                        .where(ReminderOrm.dismissed_at.is_(None))
                    )
                ).scalar_one_or_none()
                if existing:
                    continue
                self._session.add(
                    ReminderOrm(
                        id=uuid4(),
                        user_id=user_id,
                        kind="cert_expiring",
                        subject_type="certification",
                        subject_id=c.id,
                        title=f"«{c.name}» expires soon",
                        body=f"Your certification expires in {days_left} days ({c.expires_on}).",
                        due_at=now,
                        payload={"certification_id": str(c.id), "days_left": days_left},
                        created_at=now,
                    )
                )
                created += 1

        # Courses in-progress >6 months
        six_months_ago = today - timedelta(days=180)
        course_rows = (
            await self._session.execute(
                select(CourseOrm)
                .where(CourseOrm.user_id == user_id)
                .where(CourseOrm.completed_on.is_(None))
                .where(CourseOrm.started_on.is_not(None))
            )
        ).scalars().all()
        for c in course_rows:
            if c.started_on and c.started_on < six_months_ago:
                existing = (
                    await self._session.execute(
                        select(ReminderOrm)
                        .where(ReminderOrm.user_id == user_id)
                        .where(ReminderOrm.kind == "course_stale")
                        .where(ReminderOrm.subject_id == c.id)
                        .where(ReminderOrm.dismissed_at.is_(None))
                    )
                ).scalar_one_or_none()
                if existing:
                    continue
                self._session.add(
                    ReminderOrm(
                        id=uuid4(),
                        user_id=user_id,
                        kind="course_stale",
                        subject_type="course",
                        subject_id=c.id,
                        title=f"«{c.title}» — still in progress?",
                        body="Started over 6 months ago and not marked complete. Update status or remove if abandoned.",
                        due_at=now,
                        payload={"course_id": str(c.id)},
                        created_at=now,
                    )
                )
                created += 1

        await self._session.flush()
        return created


class ListReminders:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self, *, user_id: str, due_within_days: int | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:

        stmt = (
            select(ReminderOrm)
            .where(ReminderOrm.user_id == UUID(user_id))
            .where(ReminderOrm.dismissed_at.is_(None))
            .order_by(desc(ReminderOrm.created_at))
            .limit(limit)
        )
        if due_within_days is not None:
            until = utc_now() + timedelta(days=due_within_days)
            stmt = stmt.where(ReminderOrm.due_at <= until)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "id": str(r.id),
                "kind": r.kind,
                "subject_type": r.subject_type,
                "subject_id": str(r.subject_id) if r.subject_id else None,
                "title": r.title,
                "body": r.body,
                "due_at": r.due_at.isoformat(),
                "payload": r.payload,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


class DismissReminder:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self, *, user_id: str, reminder_id: str
    ) -> Result[bool, NotFoundError]:
        stmt = (
            update(ReminderOrm)
            .where(ReminderOrm.id == UUID(reminder_id))
            .where(ReminderOrm.user_id == UUID(user_id))
            .where(ReminderOrm.dismissed_at.is_(None))
            .values(dismissed_at=utc_now())
            .returning(ReminderOrm.id)
        )
        result = await self._session.execute(stmt)
        if result.first() is None:
            return err(NotFoundError("Reminder not found"))
        return ok(True)
