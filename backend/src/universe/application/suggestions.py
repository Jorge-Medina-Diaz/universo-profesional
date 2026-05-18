"""Suggestion engine — pluggable providers.

Sprint 2 ships 5 rule-based providers + 1 optional LLM provider.
Future sprints add JobMatchProvider, SalaryBenchmarkProvider, etc.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

import structlog
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.errors import NotFoundError, ValidationError
from src.shared.result import Result, err, ok
from src.shared.security import utc_now
from src.shared.uow import UnitOfWork
from src.universe.application.ports import (
    CareerPreferencesRepository,
    CertificationRepository,
    EducationRepository,
    ExperienceRepository,
    LanguageRepository,
    ProjectRepository,
    SkillRepository,
)
from src.universe.infrastructure.orm import SuggestionOrm

logger = structlog.get_logger(__name__)


# --- DTOs ---


@dataclass
class SuggestionDto:
    kind: str
    title: str
    body: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 50
    provider: str | None = None


@dataclass
class UniverseContext:
    user_id: UUID
    educations: list[Any]
    experiences: list[Any]
    projects: list[Any]
    skills: list[Any]
    certifications: list[Any]
    languages: list[Any]
    preferences: Any | None
    integrations: dict[str, Any]


# --- Provider interface ---


class SuggestionProvider(Protocol):
    name: str
    async def generate(self, ctx: UniverseContext) -> list[SuggestionDto]: ...


# --- Concrete providers ---


class MissingSkillProvider:
    """Detect skills referenced in project tech_stack but not added to skills."""

    name = "missing_skill"

    async def generate(self, ctx: UniverseContext) -> list[SuggestionDto]:
        existing = {s.name.lower() for s in ctx.skills}
        suggested: dict[str, set[str]] = {}
        for p in ctx.projects:
            for tech in (getattr(p, "tech_stack", None) or []):
                low = tech.lower()
                if low not in existing:
                    suggested.setdefault(tech, set()).add(p.name)
        out = []
        for tech, project_names in list(suggested.items())[:10]:
            out.append(
                SuggestionDto(
                    kind="add_skill",
                    title=f"Add «{tech}» to your skills",
                    body=f"Detected in {len(project_names)} project(s): "
                    + ", ".join(sorted(project_names)[:3]),
                    payload={
                        "skill_name": tech,
                        "category": "hard",
                        "evidence_projects": sorted(project_names)[:5],
                    },
                    priority=60,
                    provider=self.name,
                )
            )
        return out


class StaleSkillProvider:
    """Detect skills last used >2 years ago."""

    name = "stale_skill"

    async def generate(self, ctx: UniverseContext) -> list[SuggestionDto]:
        out = []
        current_year = utc_now().year
        for s in ctx.skills:
            last_year = getattr(s, "last_used_year", None)
            if last_year and current_year - last_year > 2:
                out.append(
                    SuggestionDto(
                        kind="review_skill",
                        title=f"Review «{s.name}» — last used {last_year}",
                        body="Consider removing it from your active skills, or marking when you last applied it.",
                        payload={"skill_id": str(s.id), "skill_name": s.name},
                        priority=30,
                        provider=self.name,
                    )
                )
        return out[:5]


class ExpiringCertProvider:
    """Certifications expiring within 60 days."""

    name = "expiring_cert"

    async def generate(self, ctx: UniverseContext) -> list[SuggestionDto]:
        today = date.today()
        out = []
        for c in ctx.certifications:
            exp = getattr(c, "expires_on", None)
            if not exp:
                continue
            days_left = (exp - today).days
            if 0 <= days_left <= 60:
                out.append(
                    SuggestionDto(
                        kind="expire_cert",
                        title=f"«{c.name}» expires in {days_left} days",
                        body="Renew before the deadline to keep it active on your CV.",
                        payload={"certification_id": str(c.id), "expires_on": exp.isoformat()},
                        priority=80,
                        provider=self.name,
                    )
                )
        return out


class IncompleteExperienceProvider:
    """Experiences with no highlights and no competences."""

    name = "incomplete_experience"

    async def generate(self, ctx: UniverseContext) -> list[SuggestionDto]:
        out = []
        for e in ctx.experiences:
            highlights = getattr(e, "highlights", None) or []
            comps = getattr(e, "competences", None) or []
            if not highlights and not comps:
                out.append(
                    SuggestionDto(
                        kind="enrich_experience",
                        title=f"Enrich «{e.role} @ {e.organization}»",
                        body="No highlights or competences recorded. Add a few bullets to make this experience CV-ready.",
                        payload={"experience_id": str(e.id)},
                        priority=55,
                        provider=self.name,
                    )
                )
        return out[:5]


class IntegrationDriftProvider:
    """If LinkedIn/GitHub last synced >30 days ago, propose a re-sync."""

    name = "integration_drift"

    async def generate(self, ctx: UniverseContext) -> list[SuggestionDto]:
        out = []
        now = utc_now()
        for provider, info in ctx.integrations.items():
            last = info.get("last_synced_at")
            if not last:
                continue
            from datetime import datetime as _dt

            last_dt = _dt.fromisoformat(last) if isinstance(last, str) else last
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=now.tzinfo)
            days = (now - last_dt).days
            if days > 30:
                out.append(
                    SuggestionDto(
                        kind="re_sync_integration",
                        title=f"Re-sync your {provider} account",
                        body=f"Last synced {days} days ago. Pull recent updates into your universe.",
                        payload={"provider": provider, "days_since_sync": days},
                        priority=40,
                        provider=self.name,
                    )
                )
        return out


# --- Engine ---


DEFAULT_PROVIDERS: list[SuggestionProvider] = [
    MissingSkillProvider(),
    StaleSkillProvider(),
    ExpiringCertProvider(),
    IncompleteExperienceProvider(),
    IntegrationDriftProvider(),
]


class GenerateSuggestions:
    def __init__(
        self,
        session: AsyncSession,
        edu: EducationRepository,
        exp: ExperienceRepository,
        proj: ProjectRepository,
        skill: SkillRepository,
        cert: CertificationRepository,
        lang: LanguageRepository,
        prefs: CareerPreferencesRepository,
        providers: list[SuggestionProvider] | None = None,
    ) -> None:
        self._session = session
        self._edu = edu
        self._exp = exp
        self._proj = proj
        self._skill = skill
        self._cert = cert
        self._lang = lang
        self._prefs = prefs
        self._providers = providers or DEFAULT_PROVIDERS

    async def execute(self, *, user_id: str) -> list[dict[str, Any]]:
        uid = UUID(user_id)
        ctx = UniverseContext(
            user_id=uid,
            educations=await self._edu.list(uid),
            experiences=await self._exp.list(uid),
            projects=await self._proj.list(uid),
            skills=await self._skill.list(uid),
            certifications=await self._cert.list(uid),
            languages=await self._lang.list(uid),
            preferences=await self._prefs.get(uid),
            integrations=await self._load_integrations(uid),
        )

        all_suggestions: list[SuggestionDto] = []
        for provider in self._providers:
            try:
                items = await provider.generate(ctx)
                all_suggestions.extend(items)
            except Exception as exc:  # noqa: BLE001
                logger.warning("suggestion_provider_failed", provider=provider.name, error=str(exc))

        # De-duplicate by (kind, payload signature)
        seen: set[tuple[str, str]] = set()
        deduped = []
        for s in all_suggestions:
            sig = (s.kind, str(sorted(s.payload.items())))
            if sig in seen:
                continue
            seen.add(sig)
            deduped.append(s)

        # Replace pending suggestions for the user with the new set
        await self._session.execute(
            update(SuggestionOrm)
            .where(SuggestionOrm.user_id == uid)
            .where(SuggestionOrm.status == "pending")
            .values(status="expired")
        )
        now = utc_now()
        for s in deduped:
            self._session.add(
                SuggestionOrm(
                    id=uuid4(),
                    user_id=uid,
                    kind=s.kind,
                    title=s.title,
                    body=s.body,
                    payload=s.payload,
                    source="rule_engine",
                    provider=s.provider,
                    status="pending",
                    priority=s.priority,
                    created_at=now,
                )
            )
        await self._session.flush()
        await self._session.commit()
        return [
            {
                "kind": s.kind,
                "title": s.title,
                "body": s.body,
                "payload": s.payload,
                "priority": s.priority,
                "provider": s.provider,
            }
            for s in deduped
        ]

    async def _load_integrations(self, user_id: UUID) -> dict[str, Any]:
        from src.integrations.infrastructure.repositories import (
            SqlExternalAccountRepository,
        )

        accounts = await SqlExternalAccountRepository(self._session).list_for_user(user_id)
        return {
            a.provider: {
                "last_synced_at": a.last_synced_at.isoformat() if a.last_synced_at else None,
                "sync_status": a.sync_status,
            }
            for a in accounts
        }


class ListSuggestions:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self,
        *,
        user_id: str,
        status: str = "pending",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(SuggestionOrm)
            .where(SuggestionOrm.user_id == UUID(user_id))
            .where(SuggestionOrm.status == status)
            .order_by(desc(SuggestionOrm.priority), desc(SuggestionOrm.created_at))
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "id": str(r.id),
                "kind": r.kind,
                "title": r.title,
                "body": r.body,
                "payload": r.payload,
                "priority": r.priority,
                "provider": r.provider,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


class ActOnSuggestion:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self, *, user_id: str, suggestion_id: str, action: str
    ) -> Result[dict[str, Any], NotFoundError | ValidationError]:
        if action not in {"accept", "reject"}:
            return err(ValidationError("action must be accept or reject"))
        new_status = "accepted" if action == "accept" else "rejected"
        stmt = (
            update(SuggestionOrm)
            .where(SuggestionOrm.id == UUID(suggestion_id))
            .where(SuggestionOrm.user_id == UUID(user_id))
            .where(SuggestionOrm.status == "pending")
            .values(status=new_status, acted_on_at=utc_now())
            .returning(SuggestionOrm.id, SuggestionOrm.kind, SuggestionOrm.payload)
        )
        result = await self._session.execute(stmt)
        row = result.first()
        if row is None:
            return err(NotFoundError("Suggestion not found or already acted on"))
        return ok({"id": str(row[0]), "kind": row[1], "payload": row[2], "status": new_status})
