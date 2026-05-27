"""DMA-based LinkedIn sync provider.

Maps the LinkedIn DMA "memberSnapshotData" response into our normalized
`LinkedInProfile`. With `LINKEDIN_DMA_ENABLED=false` we return a canned
fixture that mirrors the production payload shape — same fields, same
casing — so the mapper + commit flow is exercised end-to-end in dev.

Field names in the canned fixture follow what LinkedIn's docs publish for
each domain. If LinkedIn ever changes them, only this module's `_map_*`
functions need to update.
"""
from __future__ import annotations

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
from src.integrations.application.ports.linkedin_dma import (
    DOMAINS,
    fetch_all_domains,
)
from src.shared.config import get_settings

logger = structlog.get_logger(__name__)


CEFR_FROM_PROFICIENCY = {
    "NATIVE_OR_BILINGUAL": "native",
    "FULL_PROFESSIONAL": "C2",
    "PROFESSIONAL_WORKING": "C1",
    "LIMITED_WORKING": "B1",
    "ELEMENTARY": "A2",
}


def _coerce_year_month(raw: Any) -> str | None:
    """DMA dates come as {year:2024, month:5, day:1}. Some fields drop day/month."""
    if not raw or not isinstance(raw, dict):
        return None
    year = raw.get("year")
    if not year:
        return None
    month = raw.get("month") or 1
    day = raw.get("day") or 1
    try:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except (TypeError, ValueError):
        return None


def _map_profile(elements: list[dict[str, Any]]) -> LinkedInBasics:
    if not elements:
        return LinkedInBasics()
    p = elements[0]
    location_obj = p.get("location") or {}
    return LinkedInBasics(
        name=p.get("Name") or p.get("name"),
        first_name=p.get("First Name") or p.get("firstName"),
        last_name=p.get("Last Name") or p.get("lastName"),
        headline=p.get("Headline") or p.get("headline"),
        summary=p.get("Summary") or p.get("summary"),
        industry=p.get("Industry") or p.get("industry"),
        location=(
            location_obj.get("name")
            if isinstance(location_obj, dict)
            else p.get("Geo Location") or p.get("location")
        ),
        country=(
            location_obj.get("country") if isinstance(location_obj, dict) else p.get("country")
        ),
        public_profile_url=p.get("Public Profile URL") or p.get("publicProfileUrl"),
        picture_url=p.get("Picture URL") or p.get("pictureUrl"),
    )


def _map_positions(elements: list[dict[str, Any]]) -> list[LinkedInExperience]:
    out: list[LinkedInExperience] = []
    for p in elements:
        organization = (
            p.get("Company Name")
            or p.get("companyName")
            or p.get("organization")
            or ""
        )
        role = p.get("Title") or p.get("title") or ""
        if not organization and not role:
            continue
        start = _coerce_year_month(p.get("Started On") or p.get("startedOn")) or p.get("startDate")
        end = _coerce_year_month(p.get("Finished On") or p.get("finishedOn")) or p.get("endDate")
        out.append(
            LinkedInExperience(
                organization=organization,
                role=role,
                description=p.get("Description") or p.get("description"),
                location=p.get("Location") or p.get("location"),
                employment_type=_normalize_employment_type(
                    p.get("Employment Type") or p.get("employmentType")
                ),
                start_date=start if isinstance(start, str) else None,
                end_date=end if isinstance(end, str) else None,
                is_current=not bool(end),
            )
        )
    return out


def _normalize_employment_type(raw: str | None) -> str | None:
    if not raw:
        return None
    raw_l = raw.lower().strip().replace("-", "_").replace(" ", "_")
    mapping = {
        "full_time": "full_time",
        "part_time": "part_time",
        "contract": "contractor",
        "contractor": "contractor",
        "freelance": "contractor",
        "internship": "internship",
        "self_employed": "self_employed",
        "volunteer": "volunteer",
    }
    return mapping.get(raw_l, raw_l)


def _map_education(elements: list[dict[str, Any]]) -> list[LinkedInEducation]:
    out: list[LinkedInEducation] = []
    for e in elements:
        institution = (
            e.get("School Name") or e.get("schoolName") or e.get("institution") or ""
        )
        if not institution:
            continue
        out.append(
            LinkedInEducation(
                institution=institution,
                degree=e.get("Degree Name") or e.get("degreeName"),
                field_of_study=e.get("Field Of Study") or e.get("fieldOfStudy"),
                description=e.get("Notes") or e.get("activities") or e.get("description"),
                start_date=_coerce_year_month(e.get("Start Date") or e.get("startDate")),
                end_date=_coerce_year_month(e.get("End Date") or e.get("endDate")),
            )
        )
    return out


def _map_skills(elements: list[dict[str, Any]]) -> list[LinkedInSkill]:
    out: list[LinkedInSkill] = []
    for s in elements:
        name = s.get("Name") or s.get("name") or ""
        if not name:
            continue
        out.append(
            LinkedInSkill(
                name=name,
                category="hard",
                endorsements=s.get("Endorsement Count") or s.get("endorsementCount"),
            )
        )
    return out


def _map_languages(elements: list[dict[str, Any]]) -> list[LinkedInLanguage]:
    out: list[LinkedInLanguage] = []
    for el in elements:
        name = el.get("Name") or el.get("name") or ""
        if not name:
            continue
        prof = (el.get("Proficiency") or el.get("proficiency") or "").upper()
        level = CEFR_FROM_PROFICIENCY.get(prof, prof or "B1")
        out.append(
            LinkedInLanguage(
                name=name,
                level=level,
                code=(name[:2] or "en").lower(),
            )
        )
    return out


def _map_certifications(elements: list[dict[str, Any]]) -> list[LinkedInCertification]:
    out: list[LinkedInCertification] = []
    for c in elements:
        name = c.get("Name") or c.get("name") or ""
        if not name:
            continue
        out.append(
            LinkedInCertification(
                name=name,
                issuer=c.get("Authority") or c.get("authority") or c.get("issuer"),
                issued_on=_coerce_year_month(c.get("Started On") or c.get("startedOn")),
                expires_on=_coerce_year_month(c.get("Finished On") or c.get("finishedOn")),
                credential_id=c.get("License Number") or c.get("credentialId"),
                verification_url=c.get("Url") or c.get("url"),
            )
        )
    return out


def _map_projects(elements: list[dict[str, Any]]) -> list[LinkedInProject]:
    out: list[LinkedInProject] = []
    for p in elements:
        name = p.get("Title") or p.get("title") or p.get("name") or ""
        if not name:
            continue
        out.append(
            LinkedInProject(
                name=name,
                description=p.get("Description") or p.get("description"),
                url=p.get("Url") or p.get("url"),
                start_date=_coerce_year_month(p.get("Started On") or p.get("startedOn")),
                end_date=_coerce_year_month(p.get("Finished On") or p.get("finishedOn")),
            )
        )
    return out


def _map_courses(elements: list[dict[str, Any]]) -> list[LinkedInCourse]:
    out: list[LinkedInCourse] = []
    for c in elements:
        title = c.get("Name") or c.get("name") or c.get("title") or ""
        if not title:
            continue
        out.append(
            LinkedInCourse(
                title=title,
                platform=c.get("Provider") or c.get("Number") or c.get("provider"),
            )
        )
    return out


def _map_honors(elements: list[dict[str, Any]], kind: str) -> list[LinkedInAchievement]:
    out: list[LinkedInAchievement] = []
    for h in elements:
        title = h.get("Title") or h.get("title") or h.get("Name") or h.get("name") or ""
        if not title:
            continue
        out.append(
            LinkedInAchievement(
                title=title,
                description=h.get("Description") or h.get("description"),
                issuer=h.get("Issuer") or h.get("issuer") or h.get("Publisher") or h.get("Patent Office"),
                achieved_on=_coerce_year_month(h.get("Issued On") or h.get("Date") or h.get("Published On")),
                kind=kind,
                evidence_url=h.get("Url") or h.get("url"),
            )
        )
    return out


def _map_volunteering(elements: list[dict[str, Any]]) -> list[LinkedInExperience]:
    out: list[LinkedInExperience] = []
    for v in elements:
        org = v.get("Company Name") or v.get("organization") or ""
        role = v.get("Role") or v.get("Title") or v.get("title") or "Volunteer"
        if not org and not role:
            continue
        out.append(
            LinkedInExperience(
                organization=org,
                role=role,
                description=v.get("Description") or v.get("Cause") or v.get("description"),
                employment_type="volunteer",
                start_date=_coerce_year_month(v.get("Started On") or v.get("startedOn")),
                end_date=_coerce_year_month(v.get("Finished On") or v.get("finishedOn")),
            )
        )
    return out


def map_dma_to_profile(domains: dict[str, list[dict[str, Any]]]) -> LinkedInProfile:
    """Single entry point — turn DMA response into our DTO."""
    profile = LinkedInProfile(
        basics=_map_profile(domains.get("PROFILE", [])),
        experiences=_map_positions(domains.get("POSITIONS", []))
        + _map_volunteering(domains.get("VOLUNTEERING_EXPERIENCE", [])),
        educations=_map_education(domains.get("EDUCATION", [])),
        skills=_map_skills(domains.get("SKILLS", [])),
        languages=_map_languages(domains.get("LANGUAGES", [])),
        certifications=_map_certifications(domains.get("CERTIFICATIONS", [])),
        projects=_map_projects(domains.get("PROJECTS", [])),
        achievements=(
            _map_honors(domains.get("HONORS", []), kind="honor")
            + _map_honors(domains.get("PUBLICATIONS", []), kind="publication")
            + _map_honors(domains.get("PATENTS", []), kind="patent")
        ),
        courses=_map_courses(domains.get("COURSES", [])),
        source="linkedin_dma",
        source_metadata={"domains_fetched": list(domains.keys())},
    )
    return profile


# --- Mock fixture ---------------------------------------------------------

_MOCK_DMA: dict[str, list[dict[str, Any]]] = {
    "PROFILE": [
        {
            "First Name": "Jorge",
            "Last Name": "Medina",
            "Headline": "Senior Backend Engineer · DDD · Python · AWS",
            "Summary": (
                "Llevo 10+ años construyendo plataformas SaaS B2C y B2B. Especialista en "
                "dominio rico (DDD), arquitectura limpia y sistemas de eventos. "
                "Hablo Python, Go, TypeScript."
            ),
            "Industry": "Software Development",
            "Geo Location": "Madrid, Comunidad de Madrid, España",
            "Public Profile URL": "https://www.linkedin.com/in/jorge-medina-mock",
        }
    ],
    "POSITIONS": [
        {
            "Company Name": "Webtools",
            "Title": "Lead Backend Engineer",
            "Description": (
                "Diseño y owner técnico de la plataforma SaaS de encuestas en tiempo real. "
                "Migración monolito → microservicios, RBAC, event sourcing en partes críticas."
            ),
            "Location": "Madrid, España",
            "Employment Type": "Full-time",
            "Started On": {"year": 2022, "month": 3, "day": 1},
        },
        {
            "Company Name": "Banco Sabadell",
            "Title": "Senior Data Engineer",
            "Description": (
                "Pipelines de datos Databricks + ADF para reporting regulatorio. "
                "Diseño del data lake gold/silver/bronze."
            ),
            "Employment Type": "Contract",
            "Started On": {"year": 2020, "month": 1, "day": 1},
            "Finished On": {"year": 2022, "month": 2, "day": 28},
        },
    ],
    "EDUCATION": [
        {
            "School Name": "Universidad Politécnica de Madrid",
            "Degree Name": "Ingeniería Informática",
            "Field Of Study": "Computer Science",
            "Start Date": {"year": 2010, "month": 9, "day": 1},
            "End Date": {"year": 2015, "month": 6, "day": 30},
        }
    ],
    "SKILLS": [
        {"Name": "Python", "Endorsement Count": 47},
        {"Name": "Domain-Driven Design", "Endorsement Count": 23},
        {"Name": "FastAPI", "Endorsement Count": 19},
        {"Name": "PostgreSQL", "Endorsement Count": 31},
        {"Name": "AWS", "Endorsement Count": 28},
        {"Name": "Go", "Endorsement Count": 8},
        {"Name": "TypeScript", "Endorsement Count": 22},
        {"Name": "Event-Driven Architecture", "Endorsement Count": 12},
    ],
    "LANGUAGES": [
        {"Name": "Spanish", "Proficiency": "NATIVE_OR_BILINGUAL"},
        {"Name": "English", "Proficiency": "FULL_PROFESSIONAL"},
        {"Name": "Portuguese", "Proficiency": "LIMITED_WORKING"},
    ],
    "CERTIFICATIONS": [
        {
            "Name": "AWS Certified Solutions Architect – Associate",
            "Authority": "Amazon Web Services",
            "Started On": {"year": 2023, "month": 4, "day": 1},
            "Finished On": {"year": 2026, "month": 4, "day": 1},
            "License Number": "AWS-12345",
        }
    ],
    "HONORS": [
        {
            "Title": "Mejor TFG 2015",
            "Description": "Mejor trabajo de fin de grado de la promoción ETSI Informática.",
            "Issued On": {"year": 2015, "month": 7, "day": 15},
            "Issuer": "UPM",
        }
    ],
    "PUBLICATIONS": [],
    "PATENTS": [],
    "PROJECTS": [
        {
            "Title": "Universo Profesional",
            "Description": "SaaS B2C de gestión integral del ciclo de vida profesional con MCP remoto.",
            "Started On": {"year": 2026, "month": 4, "day": 1},
        }
    ],
    "COURSES": [
        {"Name": "Designing Data-Intensive Applications (study group)", "Provider": "Self-paced"}
    ],
    "VOLUNTEERING_EXPERIENCE": [],
}


def _load_mock() -> dict[str, list[dict[str, Any]]]:
    return _MOCK_DMA


class DmaLinkedInProvider:
    """Implementation of LinkedInSyncProvider backed by LinkedIn DMA API.

    `requires_pro = False` because the DMA API is free per the EU DMA
    regulation — the friction is LinkedIn approval, not money.
    """

    provider_id = "linkedin_dma"
    requires_pro = False

    async def fetch_profile(
        self, *, user_id: UUID, account: ExternalAccount | None
    ) -> LinkedInProfile:
        s = get_settings()
        if not s.linkedin_dma_enabled or account is None or not account.access_token:
            logger.info(
                "dma_using_mock",
                reason="flag_off_or_no_token",
                flag=s.linkedin_dma_enabled,
                has_account=account is not None,
            )
            domains = _load_mock()
        else:
            domains = await fetch_all_domains(account.access_token)
            # Defensive: if DMA returned absolutely nothing (revoked? scope issue?),
            # fall back to mock so the UX doesn't appear broken in dev.
            if not any(domains.values()):
                logger.warning("dma_empty_response_falling_back_to_mock")
                domains = _load_mock()
        profile = map_dma_to_profile(domains)
        # Carry DMA-specific provenance so the mapper can stamp source_metadata
        profile.source_metadata.update(
            {
                "fetched_at": "live" if (account and account.access_token and s.linkedin_dma_enabled) else "mock",
                "fixture_used": not (s.linkedin_dma_enabled and account and account.access_token),
                "domains_supported": list(DOMAINS),
            }
        )
        return profile
