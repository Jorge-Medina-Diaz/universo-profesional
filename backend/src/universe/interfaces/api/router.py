"""Universe REST API: /api/v1/universe/*

Each entity exposes: list, create, get-by-id, patch, delete.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel

from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.shared.uow import unit_of_work
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
