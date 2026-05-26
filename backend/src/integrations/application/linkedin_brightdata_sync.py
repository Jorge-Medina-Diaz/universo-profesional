"""Bright Data LinkedIn provider — maps the API response to our normalized DTO.

Bright Data's LinkedIn People Profile response is comprehensive (~50 top-level
fields including every section LinkedIn surfaces on a public profile). We map
to the existing `LinkedInProfile` shape so the universe importer doesn't care
which provider produced the data.

Coverage compared to other providers:
  About / summary ✓       Experience (+description) ✓
  Skills ✓                Certifications ✓
  Languages ✓             Courses ✓
  Honors / awards ✓       Publications ✓
  Patents ✓               Projects ✓
  Volunteer ✓             Recommendations ✓ (kept in source_metadata)

Gated behind PRO tier — Bright Data charges per lookup.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any
from uuid import UUID

import structlog

from src.integrations.domain.external_account import ExternalAccount
from src.integrations.domain.linkedin_profile import (
    LinkedInAchievement,
    LinkedInBasics,
    LinkedInCertification,
    LinkedInCourse,
    LinkedInEducation,
    LinkedInExperience,
    LinkedInLanguage,
    LinkedInProfile,
    LinkedInProject,
    LinkedInSkill,
)
from src.integrations.infrastructure.linkedin_brightdata_client import (
    scrape_profile,
)
from src.shared.config import get_settings

logger = structlog.get_logger(__name__)


# Bright Data emits dates in mixed formats: sometimes "Jan 2022", sometimes
# "2022-01", sometimes the full "January 2022 – Present". We normalize to ISO.

_MONTHS = {
    "jan": 1, "ene": 1, "feb": 2, "mar": 3, "apr": 4, "abr": 4, "may": 5,
    "jun": 6, "jul": 7, "aug": 8, "ago": 8, "sep": 9, "oct": 10, "nov": 11,
    "dec": 12, "dic": 12,
}


def _parse_date_str(raw: Any) -> str | None:
    """Best-effort parse of Bright Data date strings → ISO yyyy-mm-dd."""
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip().lower()
    if not s or s in ("present", "actualidad", "current", "now"):
        return None
    # Already ISO
    m = re.match(r"^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?$", s)
    if m:
        y, mo, d = m.group(1), m.group(2), m.group(3) or "1"
        try:
            return date(int(y), int(mo), int(d)).isoformat()
        except ValueError:
            return None
    # "Jan 2022", "January 2022"
    m = re.match(r"^([a-záéíóú]{3,})\.?\s+(\d{4})$", s)
    if m:
        month_name, year = m.group(1)[:3], m.group(2)
        mo = _MONTHS.get(month_name)
        if mo:
            try:
                return date(int(year), mo, 1).isoformat()
            except ValueError:
                return None
    # Bare year
    m = re.match(r"^(\d{4})$", s)
    if m:
        try:
            return date(int(m.group(1)), 1, 1).isoformat()
        except ValueError:
            return None
    return None


def _split_period(raw: Any) -> tuple[str | None, str | None, bool]:
    """Parse strings like "Jan 2022 - Present" into (start, end, is_current)."""
    if not raw or not isinstance(raw, str):
        return None, None, False
    parts = re.split(r"\s*[-–—]\s*", raw, maxsplit=1)
    if len(parts) == 1:
        return _parse_date_str(parts[0]), None, False
    start = _parse_date_str(parts[0])
    end_raw = parts[1].strip().lower()
    is_current = end_raw in ("present", "actualidad", "current", "now", "")
    end = None if is_current else _parse_date_str(parts[1])
    return start, end, is_current


def _strip_html(html: Any) -> str | None:
    if not html or not isinstance(html, str):
        return None
    text = re.sub(r"<[^>]+>", "", html).strip()
    return text or None


def _coerce_basics(raw: dict[str, Any]) -> LinkedInBasics:
    current_company = raw.get("current_company") or {}
    if not isinstance(current_company, dict):
        current_company = {}
    return LinkedInBasics(
        name=raw.get("name") or (
            f"{raw.get('first_name','')} {raw.get('last_name','')}".strip() or None
        ),
        first_name=raw.get("first_name"),
        last_name=raw.get("last_name"),
        headline=raw.get("headline") or raw.get("position"),
        summary=raw.get("about") or _strip_html(raw.get("about_html")),
        industry=raw.get("industry"),
        location=raw.get("city") or raw.get("location"),
        country=raw.get("country_code"),
        public_profile_url=raw.get("url") or raw.get("input_url"),
        picture_url=raw.get("avatar") or raw.get("default_avatar"),
    )


def _coerce_experiences(raw: dict[str, Any]) -> list[LinkedInExperience]:
    out: list[LinkedInExperience] = []
    items = raw.get("experience")
    # Bright Data returns experience=null when the profile hides job history
    # from logged-out viewers. As a fallback we synthesize a single "current"
    # experience from current_company, so the user at least sees something
    # importable. They can edit it after import.
    if items is None and raw.get("current_company"):
        cc = raw["current_company"] if isinstance(raw["current_company"], dict) else {}
        company_name = cc.get("name") or raw.get("current_company_name")
        if company_name:
            out.append(
                LinkedInExperience(
                    organization=company_name,
                    role=raw.get("position") or raw.get("headline") or "Current role",
                    description=None,
                    location=raw.get("city") or raw.get("location"),
                    is_current=True,
                )
            )
        return out
    if not isinstance(items, list):
        return out
    for e in items:
        if not isinstance(e, dict):
            continue
        company = e.get("company") or e.get("company_name") or ""
        title = e.get("title") or e.get("subtitle") or ""
        if not company and not title:
            continue
        # Bright Data sometimes gives `start_date`/`end_date` directly,
        # other times only a combined `duration_short` like "Jan 2022 - Present"
        start = _parse_date_str(e.get("start_date"))
        end = _parse_date_str(e.get("end_date"))
        is_current = bool(e.get("is_current"))
        if not start and e.get("duration_short"):
            start, end, is_current = _split_period(e["duration_short"])
        description = (
            e.get("description")
            or _strip_html(e.get("description_html"))
            or e.get("subtitle")
        )
        out.append(
            LinkedInExperience(
                organization=company,
                role=title,
                description=description,
                location=e.get("location"),
                employment_type=e.get("employment_type"),
                start_date=start,
                end_date=end,
                is_current=is_current or end is None,
            )
        )
    # Bright Data also returns volunteer experience separately
    vols = raw.get("volunteer_experience") or []
    for v in vols if isinstance(vols, list) else []:
        if not isinstance(v, dict):
            continue
        org = v.get("organization") or v.get("company") or ""
        role = v.get("role") or v.get("title") or "Volunteer"
        if not org and not role:
            continue
        start, end, is_current = _split_period(v.get("duration") or "")
        out.append(
            LinkedInExperience(
                organization=org,
                role=role,
                description=v.get("description") or v.get("cause"),
                employment_type="volunteer",
                start_date=start,
                end_date=end,
                is_current=is_current,
            )
        )
    return out


def _coerce_educations(raw: dict[str, Any]) -> list[LinkedInEducation]:
    out: list[LinkedInEducation] = []
    items = raw.get("education") or []
    # Bright Data sometimes leaves the headline (`educations_details`) on the
    # top level — use it as fallback institution name when a row in the
    # `education` array has no `title`.
    fallback_institution = raw.get("educations_details")
    if isinstance(fallback_institution, list):
        fallback_institution = fallback_institution[0] if fallback_institution else None
    if not isinstance(fallback_institution, str):
        fallback_institution = None

    for e in items if isinstance(items, list) else []:
        if not isinstance(e, dict):
            continue
        institution = (
            e.get("title")
            or e.get("school")
            or e.get("institute")
            or fallback_institution
            or ""
        )
        if not institution:
            continue
        # Bright Data packs degree+field in the `subtitle` field
        subtitle = e.get("subtitle") or ""
        degree = e.get("degree") or None
        field_of_study = e.get("field") or e.get("field_of_study")
        if subtitle and not degree:
            # "Bachelor's Degree, Computer Science"
            comma = subtitle.split(",", 1)
            degree = comma[0].strip() or None
            if not field_of_study and len(comma) > 1:
                field_of_study = comma[1].strip() or None
        start = _parse_date_str(e.get("start_year") or e.get("start_date"))
        end = _parse_date_str(e.get("end_year") or e.get("end_date"))
        if not start and e.get("duration_short"):
            start, end, _ = _split_period(e["duration_short"])
        out.append(
            LinkedInEducation(
                institution=institution,
                degree=degree,
                field_of_study=field_of_study,
                description=(
                    e.get("description")
                    or _strip_html(e.get("description_html"))
                    or e.get("activities")
                ),
                start_date=start,
                end_date=end,
            )
        )
    # Bright Data also has `educations_details` for richer info; merge if not
    # already covered
    details = raw.get("educations_details") or []
    if isinstance(details, list) and not out:
        for d in details:
            if not isinstance(d, dict):
                continue
            institution = d.get("school") or d.get("name") or ""
            if not institution:
                continue
            out.append(
                LinkedInEducation(
                    institution=institution,
                    degree=d.get("degree"),
                    field_of_study=d.get("field_of_study"),
                    description=d.get("description"),
                    start_date=_parse_date_str(d.get("start_date")),
                    end_date=_parse_date_str(d.get("end_date")),
                )
            )
    return out


def _coerce_skills(raw: dict[str, Any]) -> list[LinkedInSkill]:
    out: list[LinkedInSkill] = []
    items = raw.get("skills") or []
    for s in items if isinstance(items, list) else []:
        if isinstance(s, str):
            if s.strip():
                out.append(LinkedInSkill(name=s.strip(), category="hard"))
        elif isinstance(s, dict):
            name = s.get("name") or s.get("skill") or s.get("title")
            if not name:
                continue
            out.append(
                LinkedInSkill(
                    name=name,
                    category="hard",
                    endorsements=s.get("endorsements_count") or s.get("endorsements"),
                )
            )
    return out


_PROF_LEVEL = {
    "native or bilingual": "native",
    "native or bilingual proficiency": "native",
    "full professional": "C2",
    "full professional proficiency": "C2",
    "professional working": "C1",
    "professional working proficiency": "C1",
    "limited working": "B1",
    "limited working proficiency": "B1",
    "elementary": "A2",
    "elementary proficiency": "A2",
}


def _coerce_languages(raw: dict[str, Any]) -> list[LinkedInLanguage]:
    out: list[LinkedInLanguage] = []
    items = raw.get("languages") or []
    for l_ in items if isinstance(items, list) else []:
        if isinstance(l_, str):
            out.append(LinkedInLanguage(name=l_, level="B1", code=l_[:2].lower()))
            continue
        if not isinstance(l_, dict):
            continue
        name = l_.get("title") or l_.get("name") or l_.get("language")
        if not name:
            continue
        prof = (l_.get("subtitle") or l_.get("proficiency") or "").strip().lower()
        level = _PROF_LEVEL.get(prof, "B1")
        out.append(
            LinkedInLanguage(name=name, level=level, code=(name[:2] or "en").lower())
        )
    return out


def _coerce_certifications(raw: dict[str, Any]) -> list[LinkedInCertification]:
    out: list[LinkedInCertification] = []
    items = raw.get("certifications") or []
    for c in items if isinstance(items, list) else []:
        if not isinstance(c, dict):
            continue
        name = c.get("title") or c.get("name")
        if not name:
            continue
        issued = (
            _parse_date_str(c.get("issued_date") or c.get("issue_date"))
            or _split_period(c.get("subtitle") or "")[0]
        )
        out.append(
            LinkedInCertification(
                name=name,
                issuer=c.get("subtitle") or c.get("issuer") or c.get("authority"),
                issued_on=issued,
                expires_on=_parse_date_str(c.get("expiration_date")),
                credential_id=c.get("credential_id") or c.get("credential_number"),
                verification_url=c.get("credential_url") or c.get("url"),
            )
        )
    return out


def _coerce_projects(raw: dict[str, Any]) -> list[LinkedInProject]:
    out: list[LinkedInProject] = []
    items = raw.get("projects") or []
    for p in items if isinstance(items, list) else []:
        if not isinstance(p, dict):
            continue
        name = p.get("title") or p.get("name")
        if not name:
            continue
        start, end, _ = _split_period(p.get("subtitle") or p.get("duration") or "")
        out.append(
            LinkedInProject(
                name=name,
                description=p.get("description") or _strip_html(p.get("description_html")),
                url=p.get("url"),
                start_date=start,
                end_date=end,
            )
        )
    return out


def _coerce_courses(raw: dict[str, Any]) -> list[LinkedInCourse]:
    out: list[LinkedInCourse] = []
    items = raw.get("courses") or []
    for c in items if isinstance(items, list) else []:
        if isinstance(c, str):
            out.append(LinkedInCourse(title=c.strip()))
            continue
        if not isinstance(c, dict):
            continue
        title = c.get("title") or c.get("name")
        if not title:
            continue
        out.append(
            LinkedInCourse(
                title=title,
                platform=c.get("subtitle") or c.get("provider"),
                completed_on=_parse_date_str(c.get("date")),
            )
        )
    return out


def _coerce_achievements(raw: dict[str, Any]) -> list[LinkedInAchievement]:
    out: list[LinkedInAchievement] = []

    def _add(items: Any, kind: str) -> None:
        if not isinstance(items, list):
            return
        for h in items:
            if not isinstance(h, dict):
                continue
            title = h.get("title") or h.get("name")
            if not title:
                continue
            out.append(
                LinkedInAchievement(
                    title=title,
                    description=h.get("description") or _strip_html(h.get("description_html")),
                    issuer=h.get("issuer") or h.get("subtitle") or h.get("publisher"),
                    achieved_on=_parse_date_str(h.get("date") or h.get("issued_date")),
                    kind=kind,
                    evidence_url=h.get("url"),
                )
            )

    _add(raw.get("honors_and_awards"), "honor")
    _add(raw.get("publications"), "publication")
    _add(raw.get("patents"), "patent")
    return out


def map_brightdata_to_profile(raw: dict[str, Any]) -> LinkedInProfile:
    """Single entry point: Bright Data response → normalized LinkedInProfile."""
    profile = LinkedInProfile(
        basics=_coerce_basics(raw),
        experiences=_coerce_experiences(raw),
        educations=_coerce_educations(raw),
        skills=_coerce_skills(raw),
        languages=_coerce_languages(raw),
        certifications=_coerce_certifications(raw),
        projects=_coerce_projects(raw),
        achievements=_coerce_achievements(raw),
        courses=_coerce_courses(raw),
        source="linkedin_brightdata",
        source_metadata={
            "linkedin_id": raw.get("linkedin_id"),
            "linkedin_num_id": raw.get("linkedin_num_id"),
            "followers": raw.get("followers"),
            "connections": raw.get("connections"),
            # We don't surface these in the UI yet, but keep them around so
            # future features (LinkedIn-aware ranking, network graph) have
            # the raw signal.
            "recommendations_count": raw.get("recommendations_count"),
            "input_url": raw.get("input_url") or raw.get("url"),
        },
    )
    return profile


# --- Mock fixture for dev mode (no BRIGHTDATA_API_KEY) ----------------------

_MOCK_BRIGHTDATA: dict[str, Any] = {
    "name": "Demo Profile",
    "first_name": "Demo",
    "last_name": "Profile",
    "headline": "(mock) Senior Backend Engineer · DDD · Python · AWS",
    "about": "(mock) Sample profile shown when BRIGHTDATA_API_KEY is missing.",
    "city": "Madrid",
    "country_code": "ES",
    "experience": [
        {
            "company": "Demo Corp",
            "title": "Lead Backend Engineer",
            "description": "(mock) sample experience.",
            "duration_short": "Mar 2022 - Present",
        },
    ],
    "education": [
        {
            "title": "Universidad Demo",
            "subtitle": "Ingeniería Informática, Computer Science",
            "duration_short": "2010 - 2015",
        },
    ],
    "skills": [{"name": "Python"}, {"name": "FastAPI"}, {"name": "PostgreSQL"}],
    "languages": [
        {"title": "Spanish", "subtitle": "Native or bilingual proficiency"},
        {"title": "English", "subtitle": "Full professional proficiency"},
    ],
    "certifications": [],
    "projects": [],
    "courses": [],
    "honors_and_awards": [],
    "publications": [],
    "patents": [],
    "volunteer_experience": [],
}


class BrightDataLinkedInProvider:
    """Implementation of LinkedInSyncProvider backed by Bright Data."""

    provider_id = "linkedin_brightdata"
    requires_pro = True

    async def fetch_profile(
        self,
        *,
        user_id: UUID,
        account: ExternalAccount | None,
        linkedin_url: str | None = None,
        fresh: bool = False,
    ) -> LinkedInProfile:
        s = get_settings()
        # Prefer explicit URL; fall back to the one captured at OIDC sign-in.
        url = linkedin_url
        if not url and account is not None:
            md = account.metadata or {}
            url = md.get("public_profile_url") or md.get("linkedin_url")

        if not s.brightdata_api_key or not url:
            logger.info(
                "brightdata_using_mock",
                has_key=bool(s.brightdata_api_key),
                has_url=bool(url),
            )
            profile = map_brightdata_to_profile(_MOCK_BRIGHTDATA)
            profile.source_metadata.update({"fixture_used": True, "linkedin_url": url})
            return profile

        raw = await scrape_profile(
            api_key=s.brightdata_api_key,
            dataset_id=s.brightdata_dataset_id,
            linkedin_url=url,
        )
        profile = map_brightdata_to_profile(raw)
        profile.source_metadata.update(
            {"linkedin_url": url, "fixture_used": False, "fresh": fresh}
        )
        return profile
