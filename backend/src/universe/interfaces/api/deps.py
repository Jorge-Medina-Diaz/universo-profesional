"""DI for Universe endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.identity.interfaces.api.deps import SessionDep
from src.shared.embeddings import get_embeddings_service
from src.universe.application.use_cases import (
    AchievementCrud,
    CertificationCrud,
    CourseCrud,
    EducationCrud,
    ExperienceCrud,
    GetCareerPreferences,
    GetUniverseSummary,
    InterestCrud,
    LanguageCrud,
    ProjectCrud,
    SearchUniverse,
    SetCareerPreferences,
    SkillCrud,
    UpdateUniverseHeader,
)
from src.universe.infrastructure.repositories import (
    SqlAlchemyAchievementRepository,
    SqlAlchemyCareerPreferencesRepository,
    SqlAlchemyCertificationRepository,
    SqlAlchemyCourseRepository,
    SqlAlchemyEducationRepository,
    SqlAlchemyExperienceRepository,
    SqlAlchemyInterestRepository,
    SqlAlchemyLanguageRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemySkillRepository,
    SqlAlchemyUniverseRepository,
)
from src.universe.infrastructure.scheduler import ArqEmbeddingScheduler
from src.universe.infrastructure.semantic_search import PgVectorSemanticSearch

_scheduler = ArqEmbeddingScheduler()


def education_crud(session: SessionDep) -> EducationCrud:
    return EducationCrud(SqlAlchemyEducationRepository(session), _scheduler)


def experience_crud(session: SessionDep) -> ExperienceCrud:
    return ExperienceCrud(SqlAlchemyExperienceRepository(session), _scheduler)


def project_crud(session: SessionDep) -> ProjectCrud:
    return ProjectCrud(SqlAlchemyProjectRepository(session), _scheduler)


def skill_crud(session: SessionDep) -> SkillCrud:
    return SkillCrud(SqlAlchemySkillRepository(session), _scheduler)


def certification_crud(session: SessionDep) -> CertificationCrud:
    return CertificationCrud(SqlAlchemyCertificationRepository(session), _scheduler)


def course_crud(session: SessionDep) -> CourseCrud:
    return CourseCrud(SqlAlchemyCourseRepository(session), _scheduler)


def language_crud(session: SessionDep) -> LanguageCrud:
    return LanguageCrud(SqlAlchemyLanguageRepository(session), _scheduler)


def achievement_crud(session: SessionDep) -> AchievementCrud:
    return AchievementCrud(SqlAlchemyAchievementRepository(session), _scheduler)


def interest_crud(session: SessionDep) -> InterestCrud:
    return InterestCrud(SqlAlchemyInterestRepository(session), _scheduler)


def universe_summary(session: SessionDep) -> GetUniverseSummary:
    return GetUniverseSummary(
        SqlAlchemyUniverseRepository(session),
        SqlAlchemyEducationRepository(session),
        SqlAlchemyExperienceRepository(session),
        SqlAlchemySkillRepository(session),
        SqlAlchemyLanguageRepository(session),
        SqlAlchemyProjectRepository(session),
        SqlAlchemyCareerPreferencesRepository(session),
    )


def update_universe_header(session: SessionDep) -> UpdateUniverseHeader:
    return UpdateUniverseHeader(SqlAlchemyUniverseRepository(session))


def set_preferences(session: SessionDep) -> SetCareerPreferences:
    return SetCareerPreferences(SqlAlchemyCareerPreferencesRepository(session))


def get_preferences(session: SessionDep) -> GetCareerPreferences:
    return GetCareerPreferences(SqlAlchemyCareerPreferencesRepository(session))


def search_universe(session: SessionDep) -> SearchUniverse:
    return SearchUniverse(PgVectorSemanticSearch(session), get_embeddings_service())


EducationCrudDep = Annotated[EducationCrud, Depends(education_crud)]
ExperienceCrudDep = Annotated[ExperienceCrud, Depends(experience_crud)]
ProjectCrudDep = Annotated[ProjectCrud, Depends(project_crud)]
SkillCrudDep = Annotated[SkillCrud, Depends(skill_crud)]
CertificationCrudDep = Annotated[CertificationCrud, Depends(certification_crud)]
CourseCrudDep = Annotated[CourseCrud, Depends(course_crud)]
LanguageCrudDep = Annotated[LanguageCrud, Depends(language_crud)]
AchievementCrudDep = Annotated[AchievementCrud, Depends(achievement_crud)]
InterestCrudDep = Annotated[InterestCrud, Depends(interest_crud)]
SummaryDep = Annotated[GetUniverseSummary, Depends(universe_summary)]
UpdateHeaderDep = Annotated[UpdateUniverseHeader, Depends(update_universe_header)]
SetPrefsDep = Annotated[SetCareerPreferences, Depends(set_preferences)]
GetPrefsDep = Annotated[GetCareerPreferences, Depends(get_preferences)]
SearchDep = Annotated[SearchUniverse, Depends(search_universe)]
