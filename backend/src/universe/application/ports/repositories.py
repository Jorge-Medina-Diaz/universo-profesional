"""Repository port variables — populated by infrastructure at import time."""
from __future__ import annotations

from typing import Any

# Repository classes used directly by application layer
SqlAlchemyEducationRepository: Any = None
SqlAlchemyExperienceRepository: Any = None
SqlAlchemyProjectRepository: Any = None
SqlAlchemySkillRepository: Any = None
SqlAlchemyCertificationRepository: Any = None
SqlAlchemyCourseRepository: Any = None
SqlAlchemyLanguageRepository: Any = None
SqlAlchemyAchievementRepository: Any = None
SqlAlchemyInterestRepository: Any = None
SqlAlchemyArtifactRepository: Any = None
SqlAlchemyArchitectureDecisionRepository: Any = None
SqlAlchemyUserRubricSignalRepository: Any = None
SqlAlchemyAreaStrengthRepository: Any = None

# Helper functions used directly by application layer
update_universe_areas: Any = None
