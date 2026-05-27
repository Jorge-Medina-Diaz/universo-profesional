"""Document tools — template discovery and document retrieval for agents.

These tools let specialists query available templates and fetch document
metadata without exhausting the LLM context window.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from agno.run.base import RunContext
from agno.tools import tool
from sqlalchemy import select

from src.agents.tools._deps import require_user_id
from src.documents.infrastructure.orm import DocumentOrm
from src.shared.db import with_user_session

# Template metadata baked from the actual files in backend/templates/
# so the agent knows what exists without parsing HTML/Jinja2 at runtime.
_TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates" / "cv"

_TEMPLATE_META: dict[str, dict[str, Any]] = {
    "ats-classic": {
        "name": "ats-classic",
        "kind": "cv",
        "description": (
            "Diseño clásico optimizado para ATS (Applicant Tracking Systems). "
            "Dos columnas limpias, fuente legible, sin elementos gráficos que confundan "
            "los parsers automáticos. Ideal para corporativos, finanzas, consultoras y grandes empresas."
        ),
        "best_for": ["corporativos", "finanzas", "consultoras", "ATS-heavy"],
        "language_support": ["es", "en"],
    },
    "modern": {
        "name": "modern",
        "kind": "cv",
        "description": (
            "Diseño moderno con sidebar de skills y experiencia prominente. "
            "Las skills pills dan densidad visual sin perder claridad. "
            "Perfecto para tech, startups y scale-ups."
        ),
        "best_for": ["tech", "startups", "scale-ups", "perfiles densos"],
        "language_support": ["es", "en"],
    },
    "minimal": {
        "name": "minimal",
        "kind": "cv",
        "description": (
            "Diseño minimalista con mucho aire en la página. "
            "El espacio en blanco es protagonista. Recomendado para creativos, diseño, UX "
            "y perfiles donde la estética comunica tanto como el contenido."
        ),
        "best_for": ["creativos", "diseño", "UX", "artísticos"],
        "language_support": ["es", "en"],
    },
    "cover-letter-classic": {
        "name": "cover-letter-classic",
        "kind": "cover_letter",
        "description": (
            "Formato clásico de carta de presentación con encabezado profesional, "
            "cuerpo estructurado y cierre formal. Compatible con ATS."
        ),
        "best_for": ["corporativos", "finanzas", "consultoras"],
        "language_support": ["es", "en"],
    },
}


@tool(
    name="list_document_templates",
    description=(
        "List all available document templates (CV and cover letter) with metadata: "
        "name, kind, description, best_for audiences, and language support. "
        "Use this to recommend templates conversationally — NEVER dump the raw list."
    ),
)
def list_document_templates() -> dict[str, Any]:
    """Return available templates with metadata."""
    return {
        "templates": list(_TEMPLATE_META.values()),
        "count": len(_TEMPLATE_META),
    }


@tool(
    name="get_document_template",
    description=(
        "Get detailed metadata for a single template by name. "
        "Use after the user shows interest in a specific template."
    ),
)
def get_document_template(name: str) -> dict[str, Any]:
    """Return template structure for the given name."""
    meta = _TEMPLATE_META.get(name)
    if meta is None:
        # Try to discover if a new template was added but not in meta
        template_file = _TEMPLATE_DIR / f"{name}.html.j2"
        if template_file.exists():
            return {
                "name": name,
                "kind": "cv",
                "description": "Plantilla disponible (metadata pendiente).",
                "best_for": [],
                "language_support": ["es", "en"],
                "note": "Metadata not fully catalogued yet.",
            }
        return {"error": f"Template '{name}' not found", "available": list(_TEMPLATE_META.keys())}
    return meta


@require_user_id
@tool(
    name="get_document",
    description=(
        "Get a single document by its id. Returns full metadata including "
        "kind, template, language, tone, length, content_json summary, "
        "has_pdf, has_docx, share_token, and job_id. Use when the user "
        "refers to 'mi último CV' or a specific document."
    ),
)
async def get_document(
    run_context: RunContext,
    document_id: str,
) -> dict[str, Any]:
    """Fetch a single document's metadata and content summary."""
    user_id = run_context.user_id

    async with with_user_session(UUID(user_id)) as session:
        stmt = select(DocumentOrm).where(
            DocumentOrm.user_id == UUID(user_id),
            DocumentOrm.id == UUID(document_id),
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return {"error": "Document not found"}

        content = row.content_json or {}
        basics = content.get("basics", {})
        work = content.get("work", [])
        skills = content.get("skills", [])
        cover_body = content.get("cover_letter_body")

        return {
            "id": str(row.id),
            "kind": row.kind,
            "template": row.template,
            "language": row.language,
            "tone": row.tone,
            "length": row.length,
            "has_pdf": bool(row.pdf_path),
            "has_docx": bool(row.docx_path),
            "share_token": row.share_token,
            "job_id": str(row.job_id) if row.job_id else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "summary": {
                "name": basics.get("name"),
                "label": basics.get("label"),
                "headline_summary": basics.get("summary"),
                "cover_letter_body": cover_body,
                "experience_count": len(work),
                "skill_count": len(skills),
            },
        }
