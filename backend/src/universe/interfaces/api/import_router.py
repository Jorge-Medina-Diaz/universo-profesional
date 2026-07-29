"""Import endpoints: LinkedIn ZIP, PDF (text + LLM extraction), JSON Resume."""
from __future__ import annotations

import csv
import io
import json
import zipfile
from typing import Any

import structlog
from fastapi import APIRouter, File, UploadFile

from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.shared.uow import unit_of_work
from src.universe.interfaces.api.deps import (
    EducationCrudDep,
    ExperienceCrudDep,
    SkillCrudDep,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


_PDF_EXTRACT_SYSTEM = """Eres un parser de CVs preciso. Extraes ÚNICAMENTE datos presentes en el texto.
Devuelve EXCLUSIVAMENTE un objeto JSON válido (sin markdown, sin texto extra) con esta forma:
{
  "experience": [{"organization": "...", "role": "...", "description": "..."|null, "start_date": "YYYY-MM-DD"|null, "end_date": "YYYY-MM-DD"|null, "is_current": false}],
  "education": [{"institution": "...", "degree": "..."|null, "field_of_study": "..."|null, "start_date": "YYYY-MM-DD"|null, "end_date": "YYYY-MM-DD"|null}],
  "skills": [{"name": "...", "category": "hard"|"soft", "level": "beginner"|"intermediate"|"advanced"|"expert"|null}]
}
Reglas estrictas:
- NO inventes datos. Si algo no aparece en el texto, usa null u omite la entrada.
- Omite entradas sin lo esencial: experiencia necesita organization y role; educación necesita institution; skill necesita name.
- Fechas SIEMPRE en formato YYYY-MM-DD; si solo hay año o año-mes, completa con "-01".
- is_current=true solo si el puesto es el actual ("actualidad", "presente", "current", o sin fecha de fin explícita).
- Conserva el idioma original de los textos del CV."""


def _strip_code_fence(s: str) -> str:
    """Strip a ```json … ``` fence if the model wrapped its JSON in one."""
    s = s.strip()
    if s.startswith("```"):
        s = s[3:]
        if s[:4].lower() == "json":
            s = s[4:]
        if s.endswith("```"):
            s = s[:-3]
    return s.strip()


def _normalize_candidates(parsed: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Coerce the model output to the payload shapes the /universe endpoints accept."""
    exp = []
    for e in parsed.get("experience") or []:
        if not isinstance(e, dict) or not e.get("organization") or not e.get("role"):
            continue
        exp.append({
            "organization": str(e["organization"]).strip(),
            "role": str(e["role"]).strip(),
            "description": (str(e["description"]).strip() if e.get("description") else None),
            "start_date": e.get("start_date") or None,
            "end_date": e.get("end_date") or None,
            "is_current": bool(e.get("is_current")),
        })
    edu = []
    for e in parsed.get("education") or []:
        if not isinstance(e, dict) or not e.get("institution"):
            continue
        edu.append({
            "institution": str(e["institution"]).strip(),
            "degree": (str(e["degree"]).strip() if e.get("degree") else None),
            "field_of_study": (str(e["field_of_study"]).strip() if e.get("field_of_study") else None),
            "start_date": e.get("start_date") or None,
            "end_date": e.get("end_date") or None,
        })
    skills = []
    for s in parsed.get("skills") or []:
        if not isinstance(s, dict) or not s.get("name"):
            continue
        cat = str(s.get("category") or "hard").lower()
        skills.append({
            "name": str(s["name"]).strip(),
            "category": cat if cat in ("hard", "soft") else "hard",
            "level": (str(s["level"]).lower() if s.get("level") else None),
        })
    return {"experience": exp, "education": edu, "skills": skills}


@router.post("/pdf")
async def import_pdf(
    user_id: CurrentUserId,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Parse a CV PDF into reviewable candidates — does NOT commit.

    Pipeline: extract text with pypdf, then ask the configured LLM to structure
    it into experience / education / skill candidates. The client shows them for
    confirmation and posts the accepted ones to the /universe/{section}
    endpoints. On any failure we return a human-readable ``error`` (never a
    silently empty result) so the UI can tell the user exactly what happened.
    """
    from pypdf import PdfReader

    from src.shared.config import get_settings

    raw = await file.read()
    empty: dict[str, list[dict[str, Any]]] = {"experience": [], "education": [], "skills": []}

    # 1. Extract text.
    try:
        reader = PdfReader(io.BytesIO(raw))
        pages = [(p.extract_text() or "") for p in reader.pages]
        text = "\n".join(pages).strip()
    except Exception as exc:
        logger.warning("pdf_import_extract_failed", error=str(exc), user_id=str(user_id))
        return {"candidates": empty, "error": f"No pudimos leer el PDF: {exc}"}

    if len(text) < 40:
        return {
            "candidates": empty,
            "error": (
                "No pudimos extraer texto del PDF. Si es un PDF escaneado "
                "(una imagen), expórtalo como texto seleccionable o importa el "
                "ZIP de LinkedIn."
            ),
        }

    text = text[:24000]  # bound the prompt size; CVs are short

    # 2. LLM structured extraction.
    settings = get_settings()
    provider = settings.agents_provider_resolved
    try:
        if provider == "anthropic":
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            resp = await client.messages.create(
                model=settings.agents_specialist_model or "claude-haiku-4-5-20251001",
                max_tokens=2048,
                system=_PDF_EXTRACT_SYSTEM,
                messages=[{"role": "user", "content": text}],
            )
            content = str(resp.content[0].text)
        elif provider == "openai":
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _PDF_EXTRACT_SYSTEM},
                    {"role": "user", "content": text},
                ],
                max_tokens=2048,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            content = str(resp.choices[0].message.content)
        else:
            return {
                "candidates": empty,
                "error": "No hay un proveedor de IA configurado para analizar el CV.",
            }
    except Exception as exc:
        logger.warning("pdf_import_llm_failed", error=str(exc), user_id=str(user_id))
        return {"candidates": empty, "error": f"El análisis del CV falló: {exc}"}

    # 3. Parse + normalize.
    try:
        parsed = json.loads(_strip_code_fence(content))
        if not isinstance(parsed, dict):
            raise ValueError("not a JSON object")
    except (json.JSONDecodeError, ValueError):
        logger.warning("pdf_import_bad_json", sample=content[:200], user_id=str(user_id))
        return {
            "candidates": empty,
            "error": "El análisis devolvió un formato inesperado. Inténtalo de nuevo.",
        }

    candidates = _normalize_candidates(parsed)
    total = sum(len(v) for v in candidates.values())
    logger.info("pdf_import_parsed", user_id=str(user_id), pages=len(pages), total=total)
    return {
        "candidates": candidates,
        "meta": {"pages": len(pages), "chars": len(text), "total": total},
    }


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
    body: dict[str, Any] | None = None,
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
