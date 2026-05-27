"""Universe REST API: /api/v1/universe/*

Each entity exposes: list, create, get-by-id, patch, delete.
"""
from __future__ import annotations

from datetime import UTC
from typing import Any

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel

from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.shared.uow import unit_of_work
from src.universe.application.snapshot_service import TemporalSnapshotService
from src.universe.interfaces.api.deps import (
    AchievementCrudDep,
    CertificationCrudDep,
    CourseCrudDep,
    EducationCrudDep,
    ExperienceCrudDep,
    GetPrefsDep,
    InterestCrudDep,
    LanguageCrudDep,
    ProjectCrudDep,
    SearchDep,
    SetPrefsDep,
    SkillCrudDep,
    SummaryDep,
    UpdateHeaderDep,
)

router = APIRouter()


class UniverseHeaderPatch(BaseModel):
    headline: str | None = None
    summary: str | None = None
    photo_url: str | None = None
    current_status: str | None = None


@router.get("/summary")
async def get_summary(user_id: CurrentUserId, uc: SummaryDep) -> dict[str, Any]:
    return await uc.execute(user_id=user_id)


@router.get("/at/{iso_date}")
async def get_universe_at(
    user_id: CurrentUserId,
    session: SessionDep,
    iso_date: str,
) -> dict[str, Any]:
    """Reconstruct the user's universe as it existed on *iso_date* (YYYY-MM-DD
    or ISO-8601 datetime).  Useful for "what did my CV look like in March?"
    or time-travel debugging.
    """
    from datetime import datetime

    # Accept YYYY-MM-DD or full ISO datetime
    try:
        at = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    except ValueError:
        at = datetime.strptime(iso_date, "%Y-%m-%d").replace(tzinfo=UTC)
    svc = TemporalSnapshotService(session)
    return await svc.get_universe_at(user_id=user_id, at=at)


@router.patch("/header")
async def patch_header(
    user_id: CurrentUserId,
    body: UniverseHeaderPatch,
    uc: UpdateHeaderDep,
    session: SessionDep,
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        out = await uc.execute(
            user_id=user_id,
            patch=body.model_dump(exclude_unset=True),
            uow=uow,
        )
        await uow.commit()
    return out


# --- Educations ------------------------------------------------------------


@router.get("/education")
async def list_education(user_id: CurrentUserId, uc: EducationCrudDep) -> list[dict[str, Any]]:
    return await uc.list(user_id=user_id)


@router.post("/education", status_code=201)
async def add_education(
    user_id: CurrentUserId,
    uc: EducationCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        result = await uc.add(user_id=user_id, payload=body, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        return result.value  # type: ignore[union-attr, return-value]


@router.patch("/education/{entity_id}")
async def update_education(
    entity_id: str,
    user_id: CurrentUserId,
    uc: EducationCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        result = await uc.update(
            user_id=user_id, entity_id=entity_id, patch=body, uow=uow
        )
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        return result.value  # type: ignore[union-attr, return-value]


@router.delete("/education/{entity_id}", status_code=204)
async def delete_education(
    entity_id: str,
    user_id: CurrentUserId,
    uc: EducationCrudDep,
    session: SessionDep,
) -> None:
    async with unit_of_work(session) as uow:
        result = await uc.delete(user_id=user_id, entity_id=entity_id, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()


# --- Experiences ----------------------------------------------------------


@router.get("/experience")
async def list_experience(user_id: CurrentUserId, uc: ExperienceCrudDep) -> list[dict[str, Any]]:
    return await uc.list(user_id=user_id)


@router.post("/experience", status_code=201)
async def add_experience(
    user_id: CurrentUserId,
    uc: ExperienceCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        result = await uc.add(user_id=user_id, payload=body, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        return result.value  # type: ignore[union-attr, return-value]


@router.patch("/experience/{entity_id}")
async def update_experience(
    entity_id: str,
    user_id: CurrentUserId,
    uc: ExperienceCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        result = await uc.update(user_id=user_id, entity_id=entity_id, patch=body, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        return result.value  # type: ignore[union-attr, return-value]


@router.delete("/experience/{entity_id}", status_code=204)
async def delete_experience(
    entity_id: str,
    user_id: CurrentUserId,
    uc: ExperienceCrudDep,
    session: SessionDep,
) -> None:
    async with unit_of_work(session) as uow:
        result = await uc.delete(user_id=user_id, entity_id=entity_id, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()


# --- Projects -------------------------------------------------------------


@router.get("/project")
async def list_project(user_id: CurrentUserId, uc: ProjectCrudDep) -> list[dict[str, Any]]:
    return await uc.list(user_id=user_id)


@router.post("/project", status_code=201)
async def add_project(
    user_id: CurrentUserId,
    uc: ProjectCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        result = await uc.add(user_id=user_id, payload=body, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        return result.value  # type: ignore[union-attr, return-value]


@router.patch("/project/{entity_id}")
async def update_project(
    entity_id: str,
    user_id: CurrentUserId,
    uc: ProjectCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        result = await uc.update(user_id=user_id, entity_id=entity_id, patch=body, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        return result.value  # type: ignore[union-attr, return-value]


@router.delete("/project/{entity_id}", status_code=204)
async def delete_project(
    entity_id: str,
    user_id: CurrentUserId,
    uc: ProjectCrudDep,
    session: SessionDep,
) -> None:
    async with unit_of_work(session) as uow:
        result = await uc.delete(user_id=user_id, entity_id=entity_id, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()


# --- Skills ---------------------------------------------------------------


@router.get("/skill")
async def list_skill(user_id: CurrentUserId, uc: SkillCrudDep) -> list[dict[str, Any]]:
    return await uc.list(user_id=user_id)


@router.post("/skill", status_code=201)
async def add_skill(
    user_id: CurrentUserId,
    uc: SkillCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        result = await uc.add(user_id=user_id, payload=body, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        return result.value  # type: ignore[union-attr, return-value]


@router.patch("/skill/{entity_id}")
async def update_skill(
    entity_id: str,
    user_id: CurrentUserId,
    uc: SkillCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        result = await uc.update(user_id=user_id, entity_id=entity_id, patch=body, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        return result.value  # type: ignore[union-attr, return-value]


@router.delete("/skill/{entity_id}", status_code=204)
async def delete_skill(
    entity_id: str,
    user_id: CurrentUserId,
    uc: SkillCrudDep,
    session: SessionDep,
) -> None:
    async with unit_of_work(session) as uow:
        result = await uc.delete(user_id=user_id, entity_id=entity_id, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()


# --- Certifications, Courses, Languages, Achievements, Interests ----------


for prefix, crud_dep, label in [
    ("certification", "CertificationCrudDep", "certification"),
    ("course", "CourseCrudDep", "course"),
    ("language", "LanguageCrudDep", "language"),
    ("achievement", "AchievementCrudDep", "achievement"),
    ("interest", "InterestCrudDep", "interest"),
]:
    # Routes are declared explicitly below for clarity and OpenAPI generation.
    pass


@router.get("/certification")
async def list_certification(user_id: CurrentUserId, uc: CertificationCrudDep) -> list[dict[str, Any]]:
    return await uc.list(user_id=user_id)


@router.post("/certification", status_code=201)
async def add_certification(
    user_id: CurrentUserId,
    uc: CertificationCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        r = await uc.add(user_id=user_id, payload=body, uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()
        return r.value  # type: ignore[union-attr, return-value]


@router.patch("/certification/{entity_id}")
async def update_certification(
    entity_id: str,
    user_id: CurrentUserId,
    uc: CertificationCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        r = await uc.update(user_id=user_id, entity_id=entity_id, patch=body, uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()
        return r.value  # type: ignore[union-attr, return-value]


@router.delete("/certification/{entity_id}", status_code=204)
async def delete_certification(
    entity_id: str,
    user_id: CurrentUserId,
    uc: CertificationCrudDep,
    session: SessionDep,
) -> None:
    async with unit_of_work(session) as uow:
        r = await uc.delete(user_id=user_id, entity_id=entity_id, uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()


@router.get("/course")
async def list_course(user_id: CurrentUserId, uc: CourseCrudDep) -> list[dict[str, Any]]:
    return await uc.list(user_id=user_id)


@router.post("/course", status_code=201)
async def add_course(
    user_id: CurrentUserId,
    uc: CourseCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        r = await uc.add(user_id=user_id, payload=body, uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()
        return r.value  # type: ignore[union-attr, return-value]


@router.patch("/course/{entity_id}")
async def update_course(
    entity_id: str,
    user_id: CurrentUserId,
    uc: CourseCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        r = await uc.update(user_id=user_id, entity_id=entity_id, patch=body, uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()
        return r.value  # type: ignore[union-attr, return-value]


@router.delete("/course/{entity_id}", status_code=204)
async def delete_course(
    entity_id: str,
    user_id: CurrentUserId,
    uc: CourseCrudDep,
    session: SessionDep,
) -> None:
    async with unit_of_work(session) as uow:
        r = await uc.delete(user_id=user_id, entity_id=entity_id, uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()


@router.get("/language")
async def list_language(user_id: CurrentUserId, uc: LanguageCrudDep) -> list[dict[str, Any]]:
    return await uc.list(user_id=user_id)


@router.post("/language", status_code=201)
async def add_language(
    user_id: CurrentUserId,
    uc: LanguageCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        r = await uc.add(user_id=user_id, payload=body, uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()
        return r.value  # type: ignore[union-attr, return-value]


@router.patch("/language/{entity_id}")
async def update_language(
    entity_id: str,
    user_id: CurrentUserId,
    uc: LanguageCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        r = await uc.update(user_id=user_id, entity_id=entity_id, patch=body, uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()
        return r.value  # type: ignore[union-attr, return-value]


@router.delete("/language/{entity_id}", status_code=204)
async def delete_language(
    entity_id: str,
    user_id: CurrentUserId,
    uc: LanguageCrudDep,
    session: SessionDep,
) -> None:
    async with unit_of_work(session) as uow:
        r = await uc.delete(user_id=user_id, entity_id=entity_id, uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()


@router.get("/achievement")
async def list_achievement(user_id: CurrentUserId, uc: AchievementCrudDep) -> list[dict[str, Any]]:
    return await uc.list(user_id=user_id)


@router.post("/achievement", status_code=201)
async def add_achievement(
    user_id: CurrentUserId,
    uc: AchievementCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        r = await uc.add(user_id=user_id, payload=body, uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()
        return r.value  # type: ignore[union-attr, return-value]


@router.patch("/achievement/{entity_id}")
async def update_achievement(
    entity_id: str,
    user_id: CurrentUserId,
    uc: AchievementCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        r = await uc.update(user_id=user_id, entity_id=entity_id, patch=body, uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()
        return r.value  # type: ignore[union-attr, return-value]


@router.delete("/achievement/{entity_id}", status_code=204)
async def delete_achievement(
    entity_id: str,
    user_id: CurrentUserId,
    uc: AchievementCrudDep,
    session: SessionDep,
) -> None:
    async with unit_of_work(session) as uow:
        r = await uc.delete(user_id=user_id, entity_id=entity_id, uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()


@router.get("/interest")
async def list_interest(user_id: CurrentUserId, uc: InterestCrudDep) -> list[dict[str, Any]]:
    return await uc.list(user_id=user_id)


@router.post("/interest", status_code=201)
async def add_interest(
    user_id: CurrentUserId,
    uc: InterestCrudDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    async with unit_of_work(session) as uow:
        r = await uc.add(user_id=user_id, payload=body, uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()
        return r.value  # type: ignore[union-attr, return-value]


@router.delete("/interest/{entity_id}", status_code=204)
async def delete_interest(
    entity_id: str,
    user_id: CurrentUserId,
    uc: InterestCrudDep,
    session: SessionDep,
) -> None:
    async with unit_of_work(session) as uow:
        r = await uc.delete(user_id=user_id, entity_id=entity_id, uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()


# --- Preferences ----------------------------------------------------------


@router.get("/preferences")
async def get_preferences(user_id: CurrentUserId, uc: GetPrefsDep) -> dict[str, Any] | None:
    return await uc.execute(user_id=user_id)


@router.put("/preferences")
async def set_preferences(
    user_id: CurrentUserId,
    uc: SetPrefsDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    return await uc.execute(user_id=user_id, patch=body)


# --- Search ---------------------------------------------------------------


@router.get("/search")
async def search(
    user_id: CurrentUserId,
    uc: SearchDep,
    q: str = Query(..., min_length=2, max_length=512),
    k: int = Query(10, ge=1, le=50),
    types: str | None = Query(None),
) -> list[dict[str, Any]]:
    type_list = types.split(",") if types else None
    return await uc.execute(user_id=user_id, query=q, top_k=k, entity_types=type_list)


# --- Mark reviewed ---------------------------------------------------------


@router.post("/mark-reviewed")
async def mark_reviewed(
    user_id: CurrentUserId,
    session: SessionDep,
    body: dict[str, str] = Body(...),
) -> dict[str, Any]:
    from src.universe.application.use_cases import MarkReviewed

    uc = MarkReviewed(session)
    result = await uc.execute(
        user_id=user_id,
        entity_type=body["entity_type"],
        entity_id=body["entity_id"],
    )
    if result.is_failure:
        raise result.error  # type: ignore[union-attr]
    await session.commit()
    return result.value  # type: ignore[union-attr, return-value]


# --- Evidence linking ------------------------------------------------------


class EvidenceBody(BaseModel):
    skill_id: str
    evidence_entity_type: str
    evidence_entity_id: str
    weight: float = 1.0
    notes: str | None = None


@router.post("/evidence")
async def link_evidence(
    user_id: CurrentUserId,
    session: SessionDep,
    body: EvidenceBody,
) -> dict[str, Any]:
    from src.universe.application.use_cases import LinkEvidence

    uc = LinkEvidence(session)
    result = await uc.execute(
        user_id=user_id,
        skill_id=body.skill_id,
        evidence_entity_type=body.evidence_entity_type,
        evidence_entity_id=body.evidence_entity_id,
        weight=body.weight,
        notes=body.notes,
    )
    if result.is_failure:
        raise result.error  # type: ignore[union-attr]
    await session.commit()
    return result.value  # type: ignore[union-attr, return-value]


@router.get("/evidence")
async def list_evidence(
    user_id: CurrentUserId,
    session: SessionDep,
    skill_id: str | None = None,
) -> list[dict[str, Any]]:
    from src.universe.application.use_cases import ListEvidence

    return await ListEvidence(session).execute(user_id=user_id, skill_id=skill_id)


# --- Suggestions ----------------------------------------------------------


@router.post("/suggestions/regenerate")
async def regenerate_suggestions(
    user_id: CurrentUserId, session: SessionDep
) -> list[dict[str, Any]]:
    from src.universe.application.suggestions import GenerateSuggestions
    from src.universe.infrastructure.repositories import (
        SqlAlchemyCareerPreferencesRepository,
        SqlAlchemyCertificationRepository,
        SqlAlchemyEducationRepository,
        SqlAlchemyExperienceRepository,
        SqlAlchemyLanguageRepository,
        SqlAlchemyProjectRepository,
        SqlAlchemySkillRepository,
    )

    uc = GenerateSuggestions(
        session,
        SqlAlchemyEducationRepository(session),
        SqlAlchemyExperienceRepository(session),
        SqlAlchemyProjectRepository(session),
        SqlAlchemySkillRepository(session),
        SqlAlchemyCertificationRepository(session),
        SqlAlchemyLanguageRepository(session),
        SqlAlchemyCareerPreferencesRepository(session),
    )
    return await uc.execute(user_id=user_id)


@router.get("/suggestions")
async def list_suggestions(
    user_id: CurrentUserId,
    session: SessionDep,
    status: str = "pending",
    limit: int = 50,
) -> list[dict[str, Any]]:
    from src.universe.application.suggestions import ListSuggestions

    return await ListSuggestions(session).execute(
        user_id=user_id, status=status, limit=limit
    )


@router.post("/suggestions/{suggestion_id}/act")
async def act_on_suggestion(
    suggestion_id: str,
    user_id: CurrentUserId,
    session: SessionDep,
    body: dict[str, str] = Body(...),
) -> dict[str, Any]:
    from src.universe.application.suggestions import ActOnSuggestion

    uc = ActOnSuggestion(session)
    r = await uc.execute(user_id=user_id, suggestion_id=suggestion_id, action=body["action"])
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    await session.commit()
    return r.value  # type: ignore[union-attr, return-value]


# --- Reminders -----------------------------------------------------------


@router.get("/reminders")
async def list_reminders(
    user_id: CurrentUserId,
    session: SessionDep,
    due_within_days: int | None = None,
) -> list[dict[str, Any]]:
    from src.universe.application.reminders import ListReminders

    return await ListReminders(session).execute(
        user_id=user_id, due_within_days=due_within_days
    )


@router.post("/reminders/scan")
async def scan_reminders(
    user_id: CurrentUserId, session: SessionDep
) -> dict[str, int]:
    from uuid import UUID

    from src.universe.application.reminders import ScanReminders

    created = await ScanReminders(session).execute(user_id=UUID(user_id))
    await session.commit()
    return {"created": created}


@router.post("/reminders/{reminder_id}/dismiss")
async def dismiss_reminder(
    reminder_id: str,
    user_id: CurrentUserId,
    session: SessionDep,
) -> dict[str, Any]:
    from src.universe.application.reminders import DismissReminder

    r = await DismissReminder(session).execute(user_id=user_id, reminder_id=reminder_id)
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    await session.commit()
    return {"ok": True}


# --- Activity ------------------------------------------------------------


@router.get("/activity")
async def get_activity(
    user_id: CurrentUserId,
    session: SessionDep,
    limit: int = 50,
    since: str | None = None,
    types: str | None = None,
) -> list[dict[str, Any]]:
    from src.universe.application.use_cases import GetActivity

    type_list = types.split(",") if types else None
    return await GetActivity(session).execute(
        user_id=user_id, limit=limit, since=since, event_types=type_list
    )
