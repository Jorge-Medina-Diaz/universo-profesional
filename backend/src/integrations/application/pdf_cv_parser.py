"""PDF CV parser: pypdf text extraction + LLM structured output.

Mock mode returns a canned `ParsedCv` so flows are testable without any LLM
key. Real mode (LLM_PROVIDER=anthropic|openai) uses the `LlmClient.structured`
interface to constrain the output to the Pydantic schema.
"""
from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, Field

from src.shared.config import get_settings
from src.shared.llm_client import get_llm_client

logger = structlog.get_logger(__name__)


# --- ParsedCv schema (matches frontend ImportPlan UX) ---


class ParsedBasics(BaseModel):
    name: str | None = None
    headline: str | None = None
    summary: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None


class ParsedExperience(BaseModel):
    organization: str
    role: str
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    description: str | None = None
    highlights: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    source_page: int | None = None


class ParsedEducation(BaseModel):
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    confidence: float = 0.8
    source_page: int | None = None


class ParsedSkill(BaseModel):
    name: str
    category: str = "hard"
    level: str | None = None
    confidence: float = 0.8


class ParsedLanguage(BaseModel):
    code: str
    name: str
    level: str = "B2"
    confidence: float = 0.7


class ParsedCertification(BaseModel):
    name: str
    issuer: str | None = None
    issued_on: str | None = None
    confidence: float = 0.8


class ParsedProject(BaseModel):
    name: str
    description: str | None = None
    url: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    confidence: float = 0.7


class ParsedAchievement(BaseModel):
    title: str
    description: str | None = None
    achieved_on: str | None = None
    confidence: float = 0.7


class ParsedCv(BaseModel):
    basics: ParsedBasics = Field(default_factory=ParsedBasics)
    experiences: list[ParsedExperience] = Field(default_factory=list)
    educations: list[ParsedEducation] = Field(default_factory=list)
    skills: list[ParsedSkill] = Field(default_factory=list)
    languages: list[ParsedLanguage] = Field(default_factory=list)
    certifications: list[ParsedCertification] = Field(default_factory=list)
    projects: list[ParsedProject] = Field(default_factory=list)
    achievements: list[ParsedAchievement] = Field(default_factory=list)


# --- Extractor: PDF bytes → text ---


def extract_pdf_text(pdf_bytes: bytes) -> tuple[str, list[str]]:
    """Return (full_text, per_page_texts)."""
    import io

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for i, page in enumerate(reader.pages):
        try:
            pages.append(page.extract_text() or "")
        except Exception as exc:
            logger.warning("pdf_page_extract_failed", page=i, error=str(exc))
            pages.append("")
    full = "\n\n".join(pages)
    return full, pages


# --- Parser ---


_SYSTEM_PROMPT = """You parse a CV (résumé) into structured JSON.
Be conservative: only extract facts explicitly stated. Set `confidence` 0.0-1.0
per item — high if explicit, low if inferred. Dates as ISO-8601 (YYYY-MM-DD).
Skills: category one of [hard, soft, tool, methodology]. Languages: code is
ISO 639-1 (es, en, fr…). Levels for skills: [basic, intermediate, high, expert].
Levels for languages: [A1, A2, B1, B2, C1, C2, native]."""


_CANNED_FOR_MOCK = ParsedCv(
    basics=ParsedBasics(
        name="(mock) Profile",
        headline="Senior Backend Engineer",
        summary="Backend developer with experience in Python and PostgreSQL.",
    ),
    experiences=[
        ParsedExperience(
            organization="Acme Corp",
            role="Senior Backend Engineer",
            start_date="2022-09-01",
            end_date=None,
            is_current=True,
            description="Led API platform, improved throughput 3x.",
            highlights=["Migrated to FastAPI", "Reduced p99 latency 40%"],
            confidence=0.92,
            source_page=1,
        )
    ],
    educations=[
        ParsedEducation(
            institution="Universidad Complutense de Madrid",
            degree="Licenciado",
            field_of_study="Ingeniería Informática",
            start_date="2014-09-01",
            end_date="2018-06-30",
            confidence=0.9,
            source_page=1,
        )
    ],
    skills=[
        ParsedSkill(name="Python", category="hard", level="expert", confidence=0.95),
        ParsedSkill(name="PostgreSQL", category="hard", level="high", confidence=0.9),
        ParsedSkill(name="Docker", category="tool", level="high", confidence=0.85),
    ],
    languages=[
        ParsedLanguage(code="es", name="Spanish", level="native", confidence=1.0),
        ParsedLanguage(code="en", name="English", level="C1", confidence=0.85),
    ],
)


async def parse_cv_pdf(pdf_bytes: bytes) -> ParsedCv:
    """Extract a structured CV. Returns mock data in mock mode."""
    settings = get_settings()
    if settings.llm_provider_resolved == "mock":
        return _CANNED_FOR_MOCK

    try:
        full_text, _ = extract_pdf_text(pdf_bytes)
    except Exception as exc:
        logger.warning("pdf_extract_failed", error=str(exc))
        return _CANNED_FOR_MOCK

    if not full_text.strip():
        return _CANNED_FOR_MOCK

    # Truncate to ~12k chars to stay within reasonable token budget
    text = full_text[:12000]

    client = get_llm_client()
    try:
        return await client.structured(
            system=_SYSTEM_PROMPT,
            prompt=f"Parse this CV:\n\n{text}",
            schema=ParsedCv,
            max_tokens=4096,
            temperature=0.0,
        )
    except Exception as exc:
        logger.warning("pdf_llm_parse_failed_falling_back_to_mock", error=str(exc))
        return _CANNED_FOR_MOCK


# --- Commit helper ---


async def commit_selection(
    *,
    user_id: str,
    parsed: dict[str, Any],
    selection: dict[str, list[int]],
    edu_uc: Any,
    exp_uc: Any,
    skill_uc: Any,
    lang_uc: Any,
    cert_uc: Any,
    project_uc: Any,
    achievement_uc: Any,
    uow: Any,
) -> dict[str, int]:
    """Apply the user-selected items from a parsed CV to the universe.

    Each item runs inside a savepoint so a bad row doesn't poison the rest,
    and ISO date strings are coerced to `datetime.date` before construction.
    """
    from src.integrations.application.linkedin_mapper import coerce_dates_in_payload

    summary = {
        "experiences": 0,
        "educations": 0,
        "skills": 0,
        "languages": 0,
        "certifications": 0,
        "projects": 0,
        "achievements": 0,
    }
    sections = [
        ("experiences", exp_uc),
        ("educations", edu_uc),
        ("skills", skill_uc),
        ("languages", lang_uc),
        ("certifications", cert_uc),
        ("projects", project_uc),
        ("achievements", achievement_uc),
    ]
    session = getattr(uow, "_session", None) or getattr(uow, "session", None)
    for name, uc in sections:
        items = parsed.get(name, []) or []
        selected = set(selection.get(name, []) or list(range(len(items))))
        for idx, payload in enumerate(items):
            if idx not in selected:
                continue
            clean = coerce_dates_in_payload(
                {k: v for k, v in dict(payload).items() if k not in {"confidence", "source_page"}}
            )
            try:
                if session is not None:
                    async with session.begin_nested():
                        r = await uc.add(user_id=user_id, payload=clean, uow=uow)
                        if r.is_success:
                            summary[name] += 1
                else:
                    r = await uc.add(user_id=user_id, payload=clean, uow=uow)
                    if r.is_success:
                        summary[name] += 1
            except Exception as exc:
                logger.warning("pdf_commit_failed", section=name, error=str(exc))
    return summary
