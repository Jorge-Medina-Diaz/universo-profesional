"""Normalized LinkedIn profile DTO — shared across DMA, Proxycurl and OIDC adapters.

The point of this module is that the rest of the application doesn't care
*which* LinkedIn source produced the data. Every provider returns the same
shape, and a single mapper turns it into universe entries.

We model dates as ISO strings (or None) and keep the shape close to the universe
domain so the mapper is dumb. Anything ambiguous (proficiency strings, country
codes, BC dates) is normalized at adapter time, not at mapping time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LinkedInExperience:
    organization: str
    role: str
    description: str | None = None
    location: str | None = None
    employment_type: str | None = None  # full_time, part_time, contractor, internship, volunteer
    start_date: str | None = None  # ISO yyyy-mm-dd or yyyy-mm
    end_date: str | None = None
    is_current: bool = False


@dataclass
class LinkedInEducation:
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@dataclass
class LinkedInSkill:
    name: str
    category: str = "hard"  # hard / soft — best-effort guess; default hard
    level: str | None = None  # native / expert / high / intermediate / basic
    endorsements: int | None = None


@dataclass
class LinkedInLanguage:
    name: str
    level: str  # CEFR or LinkedIn proficiency string already normalized
    code: str | None = None  # ISO 639-1 2-letter best guess


@dataclass
class LinkedInCertification:
    name: str
    issuer: str | None = None
    issued_on: str | None = None
    expires_on: str | None = None
    credential_id: str | None = None
    verification_url: str | None = None


@dataclass
class LinkedInProject:
    name: str
    description: str | None = None
    url: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@dataclass
class LinkedInAchievement:
    title: str
    description: str | None = None
    issuer: str | None = None
    achieved_on: str | None = None
    kind: str = "honor"  # honor / publication / patent / award
    evidence_url: str | None = None


@dataclass
class LinkedInCourse:
    title: str
    platform: str | None = None
    completed_on: str | None = None


@dataclass
class LinkedInBasics:
    """Top-of-profile data."""
    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    industry: str | None = None
    location: str | None = None
    country: str | None = None
    public_profile_url: str | None = None
    picture_url: str | None = None
    email: str | None = None
    locale: str | None = None


@dataclass
class LinkedInProfile:
    """Top-level normalized profile.

    Sources fill what they have — everything is Optional. The mapper to
    universe entries skips empty sections, so providers don't need to fabricate
    placeholders.
    """
    basics: LinkedInBasics = field(default_factory=LinkedInBasics)
    experiences: list[LinkedInExperience] = field(default_factory=list)
    educations: list[LinkedInEducation] = field(default_factory=list)
    skills: list[LinkedInSkill] = field(default_factory=list)
    languages: list[LinkedInLanguage] = field(default_factory=list)
    certifications: list[LinkedInCertification] = field(default_factory=list)
    projects: list[LinkedInProject] = field(default_factory=list)
    achievements: list[LinkedInAchievement] = field(default_factory=list)
    courses: list[LinkedInCourse] = field(default_factory=list)
    # Free-form provenance: which adapter produced this + any raw fields we
    # want to keep around for debugging.
    source: str = "linkedin"  # linkedin_oidc | linkedin_dma | linkedin_proxycurl | linkedin_csv
    source_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for import_session storage (same shape as ZIP parser/PDF parser)."""
        def _asdict(x: Any) -> Any:
            if hasattr(x, "__dataclass_fields__"):
                return {k: _asdict(getattr(x, k)) for k in x.__dataclass_fields__}
            if isinstance(x, list):
                return [_asdict(i) for i in x]
            return x

        return _asdict(self)
