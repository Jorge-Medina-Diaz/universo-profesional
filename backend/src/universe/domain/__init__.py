"""Universe domain — re-export all public symbols for backward compatibility."""
from src.universe.domain.entities import (
    CANONICAL_AREAS,
    EntityType,
    EntryAdded,
    EntryRemoved,
    EntryUpdated,
    _Base,
)
from src.universe.domain.universe import Universe, UniverseCreated, UniverseUpdated

from src.universe.domain.achievement import Achievement
from src.universe.domain.architecture_decision import ADR_STATUSES, ArchitectureDecision
from src.universe.domain.artifact import Artifact, ArtifactType
from src.universe.domain.career import AreaStrength, CareerPreferences, ShapeType
from src.universe.domain.certification import Certification
from src.universe.domain.course import Course
from src.universe.domain.education import Education
from src.universe.domain.experience import Experience
from src.universe.domain.interest import Interest
from src.universe.domain.language import Language
from src.universe.domain.project import Project
from src.universe.domain.rubric_signal import SIGNAL_SECTION_KINDS, SIGNAL_STATUSES, UserRubricSignal
from src.universe.domain.skill import Skill
from src.universe.domain.skill_stack import SkillStack

__all__ = [
    "ADR_STATUSES",
    "Achievement",
    "ArchitectureDecision",
    "AreaStrength",
    "Artifact",
    "ArtifactType",
    "CANONICAL_AREAS",
    "CareerPreferences",
    "Certification",
    "Course",
    "Education",
    "EntityType",
    "EntryAdded",
    "EntryRemoved",
    "EntryUpdated",
    "Experience",
    "Interest",
    "Language",
    "Project",
    "SIGNAL_SECTION_KINDS",
    "SIGNAL_STATUSES",
    "ShapeType",
    "Skill",
    "SkillStack",
    "Universe",
    "UniverseCreated",
    "UniverseUpdated",
    "UserRubricSignal",
    "_Base",
]
