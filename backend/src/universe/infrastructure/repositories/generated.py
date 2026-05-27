"""Auto-generated CRUD repositories for entities with uniform shape."""
from __future__ import annotations

from src.universe.domain.entities import (
    Achievement,
    ArchitectureDecision,
    Certification,
    Course,
    Education,
    Experience,
    Interest,
    Project,
)
from src.universe.infrastructure.orm import (
    AchievementOrm,
    ArchitectureDecisionOrm,
    CertificationOrm,
    CourseOrm,
    EducationOrm,
    ExperienceOrm,
    InterestOrm,
    ProjectOrm,
)
from src.universe.infrastructure.repositories.base import _make_repo

SqlAlchemyEducationRepository = _make_repo(
    "SqlAlchemyEducationRepository", EducationOrm, Education
)
SqlAlchemyExperienceRepository = _make_repo(
    "SqlAlchemyExperienceRepository", ExperienceOrm, Experience
)
SqlAlchemyProjectRepository = _make_repo("SqlAlchemyProjectRepository", ProjectOrm, Project)
SqlAlchemyCertificationRepository = _make_repo(
    "SqlAlchemyCertificationRepository", CertificationOrm, Certification
)
SqlAlchemyCourseRepository = _make_repo("SqlAlchemyCourseRepository", CourseOrm, Course)
SqlAlchemyAchievementRepository = _make_repo(
    "SqlAlchemyAchievementRepository", AchievementOrm, Achievement
)
SqlAlchemyInterestRepository = _make_repo("SqlAlchemyInterestRepository", InterestOrm, Interest)
SqlAlchemyArchitectureDecisionRepository = _make_repo(
    "SqlAlchemyArchitectureDecisionRepository",
    ArchitectureDecisionOrm,
    ArchitectureDecision,
)
