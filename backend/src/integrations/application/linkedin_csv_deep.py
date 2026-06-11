"""LinkedIn 'Get a copy of your data' deep parser — all 17 CSVs."""
from __future__ import annotations

import csv
import io
import zipfile
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


CEFR_FROM_LINKEDIN = {
    "native or bilingual": "native",
    "native": "native",
    "full professional": "C2",
    "professional working": "C1",
    "limited working": "B1",
    "elementary": "A2",
    "beginner": "A1",
}


def _norm_header(s: str) -> str:
    return s.strip().lower().replace("_", " ").replace("-", " ")


def _read_csv(zf: zipfile.ZipFile, lookup: list[str]) -> list[dict[str, str]]:
    name_map = {n.split("/")[-1].lower(): n for n in zf.namelist()}
    for candidate in lookup:
        key = candidate.lower()
        if key in name_map:
            with zf.open(name_map[key]) as f:
                txt = io.TextIOWrapper(f, encoding="utf-8", errors="ignore")
                reader = csv.DictReader(txt)
                rows = []
                for row in reader:
                    # Skip preamble rows ("Notes:") that LinkedIn sometimes inlines
                    if all(v in ("", None) for v in row.values()):
                        continue
                    rows.append({_norm_header(k): (v or "").strip() for k, v in row.items()})
                return rows
    return []


def _parse_li_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    parts = raw.split()
    if len(parts) == 2:
        months = {
            "jan": "01", "feb": "02", "mar": "03", "apr": "04",
            "may": "05", "jun": "06", "jul": "07", "aug": "08",
            "sep": "09", "oct": "10", "nov": "11", "dec": "12",
        }
        m, y = parts
        mm = months.get(m[:3].lower())
        if mm and y.isdigit():
            return f"{y}-{mm}-01"
    if "/" in raw:
        try:
            mm_, dd, yyyy = raw.split("/")
            return f"{yyyy.zfill(4)}-{mm_.zfill(2)}-{dd.zfill(2)}"
        except ValueError:
            pass
    return raw


def parse_linkedin_zip(zip_bytes: bytes) -> dict[str, list[dict[str, Any]]]:
    """Parse every supported CSV in the LinkedIn export ZIP.

    Returns a dict shaped as a ParsedCv-like structure:
        {
          "basics": {...},
          "experiences": [...],
          "educations": [...],
          "skills": [...],
          "languages": [...],
          "certifications": [...],
          "achievements": [...],   # Honors + Publications + Patents merged
          "projects": [...],
          "courses": [...],
        }
    Each item carries a `source = "linkedin_csv"` flag and a normalized payload
    ready for the universe.add_* use cases.
    """
    out: dict[str, list[dict[str, Any]]] = {
        "basics": {},
        "experiences": [],
        "educations": [],
        "skills": [],
        "languages": [],
        "certifications": [],
        "achievements": [],
        "projects": [],
        "courses": [],
    }

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # Profile.csv → basics
        profile = _read_csv(zf, ["Profile.csv"])
        if profile:
            p = profile[0]
            out["basics"] = {
                "name": (p.get("first name", "") + " " + p.get("last name", "")).strip(),
                "headline": p.get("headline") or None,
                "summary": p.get("summary") or None,
                "industry": p.get("industry") or None,
                "geo_location": p.get("geo location") or p.get("location") or None,
            }

        # Positions
        for r in _read_csv(zf, ["Positions.csv"]):
            org = r.get("company name") or ""
            role = r.get("title") or ""
            if not org and not role:
                continue
            out["experiences"].append(
                {
                    "organization": org,
                    "role": role,
                    "description": r.get("description") or None,
                    "location": {"city": r.get("location")} if r.get("location") else None,
                    "start_date": _parse_li_date(r.get("started on")),
                    "end_date": _parse_li_date(r.get("finished on")),
                    "is_current": not r.get("finished on"),
                    "source_metadata": {"csv": "Positions.csv", **r},
                }
            )

        # Education
        for r in _read_csv(zf, ["Education.csv"]):
            institution = r.get("school name") or ""
            if not institution:
                continue
            out["educations"].append(
                {
                    "institution": institution,
                    "degree": r.get("degree name") or None,
                    "field_of_study": r.get("notes") or r.get("activities") or None,
                    "start_date": _parse_li_date(r.get("start date")),
                    "end_date": _parse_li_date(r.get("end date")),
                    "source_metadata": {"csv": "Education.csv", **r},
                }
            )

        # Skills
        for r in _read_csv(zf, ["Skills.csv"]):
            name = r.get("name") or ""
            if not name:
                continue
            out["skills"].append({"name": name, "category": "hard"})

        # Languages
        for r in _read_csv(zf, ["Languages.csv"]):
            name = r.get("name") or ""
            if not name:
                continue
            prof = (r.get("proficiency") or "").lower()
            level = CEFR_FROM_LINKEDIN.get(prof, "B1")
            code = (name[:2] or "en").lower()
            out["languages"].append(
                {"code": code, "name": name, "level": level}
            )

        # Certifications
        for r in _read_csv(zf, ["Certifications.csv"]):
            name = r.get("name") or ""
            if not name:
                continue
            out["certifications"].append(
                {
                    "name": name,
                    "issuer": r.get("authority") or r.get("organization") or None,
                    "issued_on": _parse_li_date(r.get("started on")),
                    "expires_on": _parse_li_date(r.get("finished on")),
                    "credential_id": r.get("license number") or None,
                    "verification_url": r.get("url") or None,
                }
            )

        # Honors → Achievements
        for r in _read_csv(zf, ["Honors.csv"]):
            title = r.get("title") or r.get("name") or ""
            if not title:
                continue
            out["achievements"].append(
                {
                    "title": title,
                    "description": r.get("description") or None,
                    "achieved_on": _parse_li_date(r.get("issued on") or r.get("date")),
                    "context": r.get("issuer") or None,
                }
            )

        # Publications → Achievements (kind=publication via context)
        for r in _read_csv(zf, ["Publications.csv"]):
            title = r.get("name") or r.get("title") or ""
            if not title:
                continue
            out["achievements"].append(
                {
                    "title": title,
                    "description": r.get("description") or None,
                    "achieved_on": _parse_li_date(r.get("date") or r.get("published on")),
                    "context": f"Publication — {r.get('publisher','')}",
                    "evidence_url": r.get("url") or None,
                }
            )

        # Patents → Achievements
        for r in _read_csv(zf, ["Patents.csv"]):
            title = r.get("title") or r.get("name") or ""
            if not title:
                continue
            out["achievements"].append(
                {
                    "title": title,
                    "description": r.get("description") or None,
                    "achieved_on": _parse_li_date(r.get("issued on") or r.get("date")),
                    "context": f"Patent — {r.get('patent office','')}",
                }
            )

        # Projects
        for r in _read_csv(zf, ["Projects.csv"]):
            name = r.get("title") or r.get("name") or ""
            if not name:
                continue
            out["projects"].append(
                {
                    "name": name,
                    "description": r.get("description") or None,
                    "start_date": _parse_li_date(r.get("started on")),
                    "end_date": _parse_li_date(r.get("finished on")),
                    "url": r.get("url") or None,
                }
            )

        # Courses
        for r in _read_csv(zf, ["Courses.csv"]):
            title = r.get("name") or r.get("title") or ""
            if not title:
                continue
            out["courses"].append(
                {
                    "title": title,
                    "platform": r.get("course number") or None,
                }
            )

        # Volunteering → Experiences (employment_type=volunteer)
        for r in _read_csv(zf, ["Volunteering.csv"]):
            org = r.get("company name") or r.get("organization") or ""
            role = r.get("role") or r.get("title") or ""
            if not org and not role:
                continue
            out["experiences"].append(
                {
                    "organization": org,
                    "role": role or "Volunteer",
                    "description": r.get("description") or r.get("cause") or None,
                    "employment_type": "volunteer",
                    "start_date": _parse_li_date(r.get("started on")),
                    "end_date": _parse_li_date(r.get("finished on")),
                    "is_current": not r.get("finished on"),
                }
            )

    return out


async def commit_parsed(
    *,
    user_id: str,
    parsed: dict[str, list[dict[str, Any]]],
    edu_uc: Any,
    exp_uc: Any,
    skill_uc: Any,
    lang_uc: Any,
    cert_uc: Any,
    achievement_uc: Any,
    project_uc: Any,
    course_uc: Any,
    uow: Any,
    selection: dict[str, list[int]] | None = None,
) -> dict[str, int]:
    """Helper to commit the parsed payload via the existing universe CRUDs.

    `selection` maps kind -> list of indices into `parsed[kind]`; when given,
    ONLY those items commit (a kind missing from the map commits nothing).
    None keeps the import-everything behavior.

    Each item is committed inside a savepoint so a single bad row doesn't
    poison the rest of the transaction. We also coerce date strings to
    `datetime.date` (importers emit ISO strings to stay JSON-friendly inside
    `import_sessions.parsed`, but the universe entities expect real dates).
    """
    from src.integrations.application.linkedin_mapper import coerce_dates_in_payload

    summary = {
        "experiences": 0,
        "educations": 0,
        "skills": 0,
        "languages": 0,
        "certifications": 0,
        "achievements": 0,
        "projects": 0,
        "courses": 0,
    }
    # Rows that failed to commit (exception OR a validation err result). These
    # used to vanish into a log line, so the import card reported only the
    # successes and the user never knew rows were dropped (no-silent-errors).
    # Surfaced in the summary as `failed` so the caller can tell the user.
    failed = 0
    session = getattr(uow, "_session", None) or getattr(uow, "session", None)
    for item, uc, key in [
        ("experiences", exp_uc, "experiences"),
        ("educations", edu_uc, "educations"),
        ("skills", skill_uc, "skills"),
        ("languages", lang_uc, "languages"),
        ("certifications", cert_uc, "certifications"),
        ("achievements", achievement_uc, "achievements"),
        ("projects", project_uc, "projects"),
        ("courses", course_uc, "courses"),
    ]:
        items = parsed.get(item, [])
        if selection is not None:
            wanted = set(selection.get(item, []))
            items = [p for i, p in enumerate(items) if i in wanted]
        for payload in items:
            clean = coerce_dates_in_payload(dict(payload))
            try:
                if session is not None:
                    async with session.begin_nested():
                        r = await uc.add(user_id=user_id, payload=clean, uow=uow)
                else:
                    r = await uc.add(user_id=user_id, payload=clean, uow=uow)
                if r.is_success:
                    summary[key] += 1
                else:
                    failed += 1
                    logger.warning(
                        "li_csv_commit_rejected", item=item, error=str(r.error)
                    )
            except Exception as exc:
                failed += 1
                logger.warning("li_csv_commit_failed", item=item, error=str(exc))
    if failed:
        summary["failed"] = failed
    return summary
