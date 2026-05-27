"""Import endpoints: LinkedIn ZIP, PDF (mock Affinda), JSON Resume, MAC."""
from __future__ import annotations

import csv
import io
import zipfile
from typing import Any

from fastapi import APIRouter, File, UploadFile

from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.shared.uow import unit_of_work
from src.universe.interfaces.api.deps import (
    EducationCrudDep,
    ExperienceCrudDep,
    SkillCrudDep,
)

router = APIRouter()


# Canned mock PDF parser response — mimics Affinda's structure.
_CANNED_PDF_PARSE = {
    "candidates": {
        "education": [
            {
                "institution": "Universidad Complutense de Madrid",
                "degree": "Licenciado",
                "field_of_study": "Ingeniería Informática",
                "start_date": "2014-09-01",
                "end_date": "2018-06-30",
                "confidence": 0.92,
            }
        ],
        "experience": [
            {
                "organization": "Acme Corp",
                "role": "Backend Engineer",
                "start_date": "2018-09-01",
                "end_date": "2022-12-31",
                "highlights": ["Mejoré el throughput de la API en 3x"],
                "confidence": 0.87,
            }
        ],
        "skills": [
            {"name": "Python", "category": "hard", "level": "expert", "confidence": 0.95},
            {"name": "PostgreSQL", "category": "hard", "level": "high", "confidence": 0.90},
        ],
    }
}


@router.post("/pdf")
async def import_pdf(
    user_id: CurrentUserId,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Mock PDF parser — in production this calls Affinda or a fallback LLM extractor.

    The endpoint returns parsed *candidates* (does not commit). The client then
    posts revised entities to the regular /universe/{section} endpoints.
    """
    _ = await file.read()  # consume the upload
    return _CANNED_PDF_PARSE


def _find_csv_files(zf: zipfile.ZipFile) -> dict[str, str | None]:
    names = {n.lower(): n for n in zf.namelist()}
    return {
        "positions": next(
            (n for k, n in names.items() if k.endswith("positions.csv")), None
        ),
        "education": next(
            (n for k, n in names.items() if k.endswith("education.csv")), None
        ),
        "skills": next(
            (n for k, n in names.items() if k.endswith("skills.csv")), None
        ),
    }


async def _parse_li_experiences(
    zf: zipfile.ZipFile,
    filename: str,
    user_id: CurrentUserId,
    exp_uc: ExperienceCrudDep,
    uow: Any,
) -> int:
    count = 0
    with zf.open(filename) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, "utf-8"))
        for row in reader:
            payload = {
                "organization": row.get("Company Name", "").strip(),
                "role": row.get("Title", "").strip(),
                "description": row.get("Description", "").strip() or None,
                "start_date": _parse_li_date(row.get("Started On")),
                "end_date": _parse_li_date(row.get("Finished On")),
                "is_current": not row.get("Finished On"),
            }
            if not payload["organization"] or not payload["role"]:
                continue
            r = await exp_uc.add(user_id=user_id, payload=payload, uow=uow)
            if r.is_success:
                count += 1
    return count


async def _parse_li_educations(
    zf: zipfile.ZipFile,
    filename: str,
    user_id: CurrentUserId,
    edu_uc: EducationCrudDep,
    uow: Any,
) -> int:
    count = 0
    with zf.open(filename) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, "utf-8"))
        for row in reader:
            payload = {
                "institution": row.get("School Name", "").strip(),
                "degree": row.get("Degree Name", "").strip() or None,
                "field_of_study": row.get("Notes", "").strip() or None,
                "start_date": _parse_li_date(row.get("Start Date")),
                "end_date": _parse_li_date(row.get("End Date")),
            }
            if not payload["institution"]:
                continue
            r = await edu_uc.add(user_id=user_id, payload=payload, uow=uow)
            if r.is_success:
                count += 1
    return count


async def _parse_li_skills(
    zf: zipfile.ZipFile,
    filename: str,
    user_id: CurrentUserId,
    skill_uc: SkillCrudDep,
    uow: Any,
) -> int:
    count = 0
    with zf.open(filename) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, "utf-8"))
        for row in reader:
            name = row.get("Name", "").strip()
            if not name:
                continue
            payload = {"name": name, "category": "hard"}
            r = await skill_uc.add(user_id=user_id, payload=payload, uow=uow)
            if r.is_success:
                count += 1
    return count


@router.post("/linkedin")
async def import_linkedin_zip(
    user_id: CurrentUserId,
    edu_uc: EducationCrudDep,
    exp_uc: ExperienceCrudDep,
    skill_uc: SkillCrudDep,
    session: SessionDep,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Parse LinkedIn 'Get a copy of your data' ZIP and commit entities.

    Looks for: Positions.csv, Education.csv, Skills.csv (LinkedIn's documented format).
    Returns a summary count.
    """
    contents = await file.read()
    summary = {"educations": 0, "experiences": 0, "skills": 0, "errors": []}
    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as zf:
            files = _find_csv_files(zf)
            async with unit_of_work(session) as uow:
                if files.get("positions"):
                    summary["experiences"] = await _parse_li_experiences(
                        zf, files["positions"], user_id, exp_uc, uow
                    )
                if files.get("education"):
                    summary["educations"] = await _parse_li_educations(
                        zf, files["education"], user_id, edu_uc, uow
                    )
                if files.get("skills"):
                    summary["skills"] = await _parse_li_skills(
                        zf, files["skills"], user_id, skill_uc, uow
                    )
                await uow.commit()
    except Exception as exc:
        summary["errors"].append(str(exc))
    return summary


@router.post("/json-resume")
async def import_json_resume(
    user_id: CurrentUserId,
    edu_uc: EducationCrudDep,
    exp_uc: ExperienceCrudDep,
    skill_uc: SkillCrudDep,
    session: SessionDep,
    body: dict[str, Any] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Import JSON Resume v1.0.0."""
    if body is None:
        return {"errors": ["body required"]}
    summary = {"educations": 0, "experiences": 0, "skills": 0}
    async with unit_of_work(session) as uow:
        for w in body.get("work", []) or []:
            payload = {
                "organization": w.get("name") or w.get("company") or "",
                "role": w.get("position") or "",
                "description": w.get("summary"),
                "highlights": w.get("highlights", []),
                "start_date": w.get("startDate"),
                "end_date": w.get("endDate"),
            }
            if not payload["organization"] or not payload["role"]:
                continue
            r = await exp_uc.add(user_id=user_id, payload=payload, uow=uow)
            if r.is_success:
                summary["experiences"] += 1
        for e in body.get("education", []) or []:
            payload = {
                "institution": e.get("institution") or "",
                "degree": e.get("studyType"),
                "field_of_study": e.get("area"),
                "start_date": e.get("startDate"),
                "end_date": e.get("endDate"),
            }
            if not payload["institution"]:
                continue
            r = await edu_uc.add(user_id=user_id, payload=payload, uow=uow)
            if r.is_success:
                summary["educations"] += 1
        for s in body.get("skills", []) or []:
            payload = {
                "name": s.get("name") or "",
                "category": "hard",
                "level": (s.get("level") or "").lower() or None,
            }
            if not payload["name"]:
                continue
            r = await skill_uc.add(user_id=user_id, payload=payload, uow=uow)
            if r.is_success:
                summary["skills"] += 1
        await uow.commit()
    return summary


def _parse_li_date(raw: str | None) -> str | None:
    if not raw:
        return None
    # LinkedIn exports usually "Mon YYYY" or "MM/DD/YYYY"
    raw = raw.strip()
    parts = raw.split()
    if len(parts) == 2:
        months = {
            "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
            "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
            "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
        }
        m, y = parts
        mm = months.get(m[:3])
        if mm and y.isdigit():
            return f"{y}-{mm}-01"
    return raw  # fall through; pydantic on the entity side will coerce
