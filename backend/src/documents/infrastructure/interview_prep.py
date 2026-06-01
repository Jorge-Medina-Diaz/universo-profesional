"""Interview-prep generation (R16).

Grounded-first, mirroring the document LLM client: compose a usable prep from
the user's REAL universe entities + the parsed JD (works with no LLM key), then
— when a provider is configured — enrich it with one LLM pass that may only
rephrase/expand grounded facts (never invent experience). On any LLM failure we
return the grounded base. Lives in infrastructure (reuses the LLM client +
entity composition); the jobs router orchestrates persistence.
"""
from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.documents.infrastructure.llm_client import (
    MockLlmClient,
    _facts_for_prompt,
    _job_for_prompt,
)
from src.shared.config import get_settings
from src.shared.llm_client import get_llm_client

logger = structlog.get_logger(__name__)


class StarDraft(BaseModel):
    prompt: str = Field(
        description="The behavioural question / achievement this STAR answer addresses."
    )
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""


class InterviewPrepArtifacts(BaseModel):
    research_brief: str = Field(
        description="Concise brief: the role, what the company likely values, and how the "
        "candidate's real strengths map to it. Spanish."
    )
    questions: list[str] = Field(
        default_factory=list,
        description="8-12 likely interview questions: behavioural + role-specific to the JD.",
    )
    star_drafts: list[StarDraft] = Field(
        default_factory=list,
        description="3-5 STAR drafts, each grounded in ONE of the candidate's REAL experiences.",
    )


def compose_grounded_prep(
    job_summary: dict[str, Any], facts: dict[str, Any]
) -> dict[str, Any]:
    """Deterministic prep from the parsed JD + the user's real entities. No LLM."""
    title = job_summary.get("title") or "el puesto"
    company = job_summary.get("company") or "la empresa"
    must = [m for m in (job_summary.get("must_haves") or []) if m]
    keywords = [k for k in (job_summary.get("ats_keywords") or []) if k]
    work = facts.get("work") or []
    skills = [s.get("name") for s in (facts.get("skills") or []) if s.get("name")]

    relevant = must or keywords
    matched = [
        s
        for s in skills
        if any(s.lower() in r.lower() or r.lower() in s.lower() for r in relevant)
    ]

    brief = [f"Puesto: {title} en {company}."]
    if must:
        brief.append("Requisitos clave: " + ", ".join(must[:8]) + ".")
    if matched:
        brief.append("Tus fortalezas relevantes: " + ", ".join(matched[:8]) + ".")
    brief.append(
        "Antes de la entrevista, investiga la misión y el producto de la empresa, "
        "noticias recientes y el perfil de quien te entrevistará."
    )

    questions = [
        f"¿Por qué te interesa el puesto de {title} en {company}?",
        "Cuéntame un proyecto del que estés especialmente orgulloso/a y tu rol exacto.",
        "Describe una situación de conflicto en equipo y cómo la resolviste.",
        "Háblame de un fracaso o error y qué aprendiste de él.",
    ]
    for r in relevant[:6]:
        questions.append(f"Cuéntame tu experiencia concreta con {r}.")

    star_drafts: list[dict[str, Any]] = []
    for w in work[:4]:
        org = w.get("name") or ""
        role = w.get("position") or ""
        highlights = w.get("highlights") or []
        label = " en ".join(p for p in [role, org] if p) or "una experiencia reciente"
        star_drafts.append(
            {
                "prompt": f"Logro destacado ({label})",
                "situation": w.get("summary") or f"Mi etapa como {label}.",
                "task": "",
                "action": "",
                "result": highlights[0] if highlights else "",
            }
        )

    return {
        "research_brief": " ".join(brief),
        "questions": questions,
        "star_drafts": star_drafts,
    }


async def generate_prep_artifacts(
    session: AsyncSession, job_summary: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    """Return (artifacts, generated_by). Grounded base, LLM-enriched when a
    provider is configured; degrades to grounded on any LLM failure."""
    facts = await MockLlmClient(session).generate_cv_bullets(
        job_summary=job_summary, retrieved=[], language="es", tone=None
    )
    grounded = compose_grounded_prep(job_summary, facts)

    settings = get_settings()
    if settings.llm_provider_resolved == "mock":
        return grounded, "grounded"

    system = (
        "Eres un coach de entrevistas. Usando SOLO el perfil factual del candidato, "
        "produce preparación de entrevista: un brief de investigación conciso, un banco "
        "de preguntas (conductuales + específicas del puesto) y borradores STAR anclados "
        "en las experiencias REALES del candidato. Nunca inventes experiencia, empresas "
        "ni habilidades que no aparezcan en los hechos. Responde en español."
    )
    prompt = (
        "## Perfil del candidato (hechos)\n"
        f"{_facts_for_prompt(facts)}\n\n"
        "## Oferta objetivo\n"
        f"{_job_for_prompt(job_summary)}\n\n"
        "Devuelve research_brief, questions (8-12) y star_drafts (3-5, cada uno anclado "
        "en una experiencia real con Situación/Tarea/Acción/Resultado)."
    )
    try:
        llm = get_llm_client()
        result = await llm.structured(
            system=system,
            prompt=prompt,
            schema=InterviewPrepArtifacts,
            max_tokens=2500,
            temperature=0.5,
        )
        return (
            {
                "research_brief": result.research_brief,
                "questions": result.questions,
                "star_drafts": [d.model_dump() for d in result.star_drafts],
            },
            f"ai/{settings.llm_provider_resolved}",
        )
    except Exception as exc:
        logger.warning("interview_prep_llm_failed_using_grounded", error=str(exc))
        return grounded, "grounded"
