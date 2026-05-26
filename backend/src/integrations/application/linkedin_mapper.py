"""LinkedInProfile → universe entries.

A single mapper consumed by both `LinkedInSyncFromDma` and
`LinkedInSyncFromProxycurl`. Inputs are the normalized DTO, outputs are the
universe CRUD `add()` payloads — same shape that `commit_parsed`/`commit_selection`
already accept, so we slot into the existing import_session flow.

Dedup strategy:
  * experiences/educations: case-insensitive (organization+role) / (institution+degree+year)
  * skills: lower(name)
  * languages: lower(code)
  * certifications: lower(name)+issuer
  * projects: name+url
  * courses: lower(title)
  * achievements: lower(title)+achieved_on

Note: dates remain ISO strings in the *parsed* payload (so it serializes cleanly
to JSON inside `import_sessions.parsed`); they are coerced to `datetime.date`
right before the entity is constructed (see `_coerce_dates_in_payload`).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from src.integrations.domain.linkedin_profile import LinkedInProfile

_DATE_KEYS = {
    "start_date",
    "end_date",
    "issued_on",
    "expires_on",
    "achieved_on",
    "started_on",
    "completed_on",
}


def _to_date(raw: Any) -> Any:
    """Parse an ISO yyyy-mm-dd (or yyyy-mm) into a `datetime.date`.

    Returns the original value unchanged if it isn't a string we can parse.
    """
    if raw is None or isinstance(raw, date):
        return raw
    if not isinstance(raw, str):
        return raw
    s = raw.strip()
    if not s:
        return None
    # yyyy-mm-dd
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            return date.fromisoformat(s)
        except ValueError:
            return raw
    # yyyy-mm — pad day to 01
    if len(s) == 7 and s[4] == "-":
        try:
            return date.fromisoformat(f"{s}-01")
        except ValueError:
            return raw
    # yyyy
    if len(s) == 4 and s.isdigit():
        try:
            return date(int(s), 1, 1)
        except ValueError:
            return raw
    return raw


def coerce_dates_in_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of `payload` with any `_date` field coerced to `date`.

    Importers (LinkedIn ZIP, DMA, Proxycurl, PDF) all emit dates as ISO
    strings to keep the import session JSON-friendly. The universe entities
    expect `datetime.date`, so we coerce just before construction.
    """
    out = dict(payload)
    for k in list(out.keys()):
        if k in _DATE_KEYS:
            out[k] = _to_date(out[k])
    return out


def profile_to_universe_payloads(profile: LinkedInProfile) -> dict[str, Any]:
    """Convert a LinkedInProfile to the same shape ZIP/PDF parsers return.

    The returned dict is suitable for:
      * Persisting in `import_sessions.parsed`
      * Passing to `commit_parsed` or `commit_selection`
      * Serializing to JSON for chat-driven HITL confirmation
    """
    src_meta_base = {"source": profile.source, **profile.source_metadata}

    basics = {
        "name": profile.basics.name,
        "headline": profile.basics.headline,
        "summary": profile.basics.summary,
        "industry": profile.basics.industry,
        "location": profile.basics.location,
        "country": profile.basics.country,
        "public_profile_url": profile.basics.public_profile_url,
        "picture_url": profile.basics.picture_url,
    }

    experiences = [
        {
            "organization": e.organization,
            "role": e.role,
            "description": e.description,
            "location": {"city": e.location} if e.location else None,
            "employment_type": e.employment_type,
            "start_date": e.start_date,
            "end_date": e.end_date,
            "is_current": e.is_current,
            "source_metadata": dict(src_meta_base),
        }
        for e in profile.experiences
        if e.organization or e.role
    ]

    educations = [
        {
            "institution": ed.institution,
            "degree": ed.degree,
            "field_of_study": ed.field_of_study,
            "description": ed.description,
            "start_date": ed.start_date,
            "end_date": ed.end_date,
            "source_metadata": dict(src_meta_base),
        }
        for ed in profile.educations
        if ed.institution
    ]

    skills = [
        {
            "name": s.name,
            "category": s.category or "hard",
            "level": s.level,
            "source_metadata": {
                **src_meta_base,
                "endorsements": s.endorsements,
            },
        }
        for s in profile.skills
        if s.name
    ]

    languages = [
        {
            "code": (l.code or l.name[:2]).lower(),
            "name": l.name,
            "level": l.level or "B1",
            "source_metadata": dict(src_meta_base),
        }
        for l in profile.languages
        if l.name
    ]

    certifications = [
        {
            "name": c.name,
            "issuer": c.issuer,
            "issued_on": c.issued_on,
            "expires_on": c.expires_on,
            "credential_id": c.credential_id,
            "verification_url": c.verification_url,
            "source_metadata": dict(src_meta_base),
        }
        for c in profile.certifications
        if c.name
    ]

    projects = [
        {
            "name": p.name,
            "description": p.description,
            "url": p.url,
            "start_date": p.start_date,
            "end_date": p.end_date,
            "source_metadata": dict(src_meta_base),
        }
        for p in profile.projects
        if p.name
    ]

    achievements = [
        {
            "title": a.title,
            "description": a.description,
            "context": a.issuer,
            "achieved_on": a.achieved_on,
            "evidence_url": a.evidence_url,
            "source_metadata": {**src_meta_base, "kind": a.kind},
        }
        for a in profile.achievements
        if a.title
    ]

    courses = [
        {
            "title": c.title,
            "platform": c.platform,
            "completed_on": c.completed_on,
            "source_metadata": dict(src_meta_base),
        }
        for c in profile.courses
        if c.title
    ]

    return {
        "basics": basics,
        "experiences": experiences,
        "educations": educations,
        "skills": skills,
        "languages": languages,
        "certifications": certifications,
        "projects": projects,
        "achievements": achievements,
        "courses": courses,
    }
