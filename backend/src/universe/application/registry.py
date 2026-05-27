"""Central CRUD registry — entity kind → use-case class + repository class + deps key.

Used by coherence (upsert) and MCP (direct CRUD) so the two can never drift.
Every entity kind that appears in ``GRAPH_REGISTRY`` and supports full CRUD
must be registered here.
"""
from __future__ import annotations

from typing import Any

from src.universe.application.use_cases import (
    AchievementCrud,
    ArchitectureDecisionCrud,
    ArtifactCrud,
    CertificationCrud,
    CourseCrud,
    EducationCrud,
    ExperienceCrud,
    InterestCrud,
    LanguageCrud,
    ProjectCrud,
    SkillCrud,
)
from src.universe.application.ports.repositories import (
    SqlAlchemyAchievementRepository,
    SqlAlchemyArchitectureDecisionRepository,
    SqlAlchemyArtifactRepository,
    SqlAlchemyCertificationRepository,
    SqlAlchemyCourseRepository,
    SqlAlchemyEducationRepository,
    SqlAlchemyExperienceRepository,
    SqlAlchemyInterestRepository,
    SqlAlchemyLanguageRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemySkillRepository,
)


class CrudRegistry:
    """Immutable registry mapping each universe entity kind to its
    application CRUD use-case, infrastructure repository class, and the
    key used in ``_session_only_deps`` style dependency dicts.
    """

    # (crud_class, repo_class, deps_key)
    _DATA: dict[str, tuple[Any, Any, str]] = {
        "skill": (SkillCrud, SqlAlchemySkillRepository, "skill_repo"),
        "experience": (ExperienceCrud, SqlAlchemyExperienceRepository, "exp_repo"),
        "education": (EducationCrud, SqlAlchemyEducationRepository, "edu_repo"),
        "project": (ProjectCrud, SqlAlchemyProjectRepository, "proj_repo"),
        "certification": (CertificationCrud, SqlAlchemyCertificationRepository, "cert_repo"),
        "course": (CourseCrud, SqlAlchemyCourseRepository, "course_repo"),
        "language": (LanguageCrud, SqlAlchemyLanguageRepository, "lang_repo"),
        "achievement": (AchievementCrud, SqlAlchemyAchievementRepository, "ach_repo"),
        "interest": (InterestCrud, SqlAlchemyInterestRepository, "int_repo"),
        "artifact": (ArtifactCrud, SqlAlchemyArtifactRepository, "artifact_repo"),
        "architecture_decision": (
            ArchitectureDecisionCrud,
            SqlAlchemyArchitectureDecisionRepository,
            "arch_decision_repo",
        ),
    }

    @classmethod
    def kinds(cls) -> set[str]:
        """All registered entity kinds."""
        return set(cls._DATA.keys())

    @classmethod
    def get_crud_class(cls, kind: str) -> Any:
        """Return the CRUD use-case class for *kind*.

        Raises ``KeyError`` if the kind is not registered.
        """
        return cls._DATA[kind][0]

    @classmethod
    def get_repo_class(cls, kind: str) -> Any:
        """Return the SQLAlchemy repository class for *kind*.

        Raises ``KeyError`` if the kind is not registered.
        """
        return cls._DATA[kind][1]

    @classmethod
    def get_repo_key(cls, kind: str) -> str:
        """Return the dependency-dict key for *kind* (e.g. ``'skill_repo'``).

        Raises ``KeyError`` if the kind is not registered.
        """
        return cls._DATA[kind][2]

    @classmethod
    def get(cls, kind: str) -> tuple[Any, Any, str]:
        """Return the full 3-tuple *(crud_class, repo_class, deps_key)*."""
        return cls._DATA[kind]
