"""SQLAlchemy implementations of Universe ports.

Every entity has an analogous repository following the same pattern. We
intentionally keep mapping functions explicit rather than using a generic
mapper — the entities differ enough that magic mapping leaks more bugs
than the duplication costs.
"""
from __future__ import annotations

from src.universe.infrastructure.repositories.base import (
    _BaseRepo,
    _build_repo_methods,
    _entity_to_orm_kwargs,
    _make_repo,
    _orm_to_entity,
)
from src.universe.infrastructure.repositories.custom import (
    SqlAlchemyAreaStrengthRepository,
    SqlAlchemyArtifactRepository,
    SqlAlchemyCareerPreferencesRepository,
    SqlAlchemyLanguageRepository,
    SqlAlchemySkillRepository,
    SqlAlchemySkillStackRepository,
    SqlAlchemyUniverseRepository,
    SqlAlchemyUserRubricSignalRepository,
    update_universe_areas,
)
from src.universe.infrastructure.repositories.generated import (
    SqlAlchemyAchievementRepository,
    SqlAlchemyArchitectureDecisionRepository,
    SqlAlchemyCertificationRepository,
    SqlAlchemyCourseRepository,
    SqlAlchemyEducationRepository,
    SqlAlchemyExperienceRepository,
    SqlAlchemyInterestRepository,
    SqlAlchemyProjectRepository,
)

# ---------------------------------------------------------------------------
# Wire module-level ports so application layer stays import-clean.
# ---------------------------------------------------------------------------
from src.universe.application.ports import repositories as _repo_port  # noqa: E402

_repo_port.SqlAlchemyEducationRepository = SqlAlchemyEducationRepository
_repo_port.SqlAlchemyExperienceRepository = SqlAlchemyExperienceRepository
_repo_port.SqlAlchemyProjectRepository = SqlAlchemyProjectRepository
_repo_port.SqlAlchemySkillRepository = SqlAlchemySkillRepository
_repo_port.SqlAlchemyCertificationRepository = SqlAlchemyCertificationRepository
_repo_port.SqlAlchemyCourseRepository = SqlAlchemyCourseRepository
_repo_port.SqlAlchemyLanguageRepository = SqlAlchemyLanguageRepository
_repo_port.SqlAlchemyAchievementRepository = SqlAlchemyAchievementRepository
_repo_port.SqlAlchemyInterestRepository = SqlAlchemyInterestRepository
_repo_port.SqlAlchemyArtifactRepository = SqlAlchemyArtifactRepository
_repo_port.SqlAlchemyArchitectureDecisionRepository = SqlAlchemyArchitectureDecisionRepository
_repo_port.SqlAlchemyUserRubricSignalRepository = SqlAlchemyUserRubricSignalRepository
_repo_port.SqlAlchemyAreaStrengthRepository = SqlAlchemyAreaStrengthRepository
_repo_port.update_universe_areas = update_universe_areas

__all__ = [
    "_BaseRepo",
    "_build_repo_methods",
    "_entity_to_orm_kwargs",
    "_make_repo",
    "_orm_to_entity",
    "SqlAlchemyAchievementRepository",
    "SqlAlchemyArchitectureDecisionRepository",
    "SqlAlchemyAreaStrengthRepository",
    "SqlAlchemyArtifactRepository",
    "SqlAlchemyCareerPreferencesRepository",
    "SqlAlchemyCertificationRepository",
    "SqlAlchemyCourseRepository",
    "SqlAlchemyEducationRepository",
    "SqlAlchemyExperienceRepository",
    "SqlAlchemyInterestRepository",
    "SqlAlchemyLanguageRepository",
    "SqlAlchemyProjectRepository",
    "SqlAlchemySkillRepository",
    "SqlAlchemySkillStackRepository",
    "SqlAlchemyUniverseRepository",
    "SqlAlchemyUserRubricSignalRepository",
    "update_universe_areas",
]
