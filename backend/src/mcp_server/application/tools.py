"""MCP tools registry — Sprint 2 expansion to ~35 tools covering the full lifecycle.

Categories:
  * Universe write (add/update/delete) for each of the 9 entities + preferences + header
  * Universe read (get_profile, get_universe_summary, list_skills, search)
  * Integrations (connect/sync/disconnect + import linkedin/pdf)
  * Suggestions + Reminders + Activity
  * Documents (list, get, share, generate_cv)
  * Evidence + Avatar + Mark reviewed

Each tool delegates to the same use cases used by REST routes — no duplicate logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.mcp_server.application.handlers import (
    _h_apply_suggestion,
    _h_commit_import_session,
    _h_disconnect_account,
    _h_dismiss_reminder,
    _h_generate_cv,
    _h_get_activity,
    _h_get_avatar_url,
    _h_get_document,
    _h_get_prefs,
    _h_get_profile,
    _h_get_user_tier,
    _h_import_linkedin_zip,
    _h_import_pdf_cv,
    _h_link_evidence,
    _h_list_connections,
    _h_list_documents,
    _h_list_reminders,
    _h_list_skills,
    _h_list_suggestions,
    _h_mark_reviewed,
    _h_match_job,
    _h_scan_reminders,
    _h_search,
    _h_set_avatar,
    _h_set_prefs,
    _h_set_user_tier,
    _h_share_document,
    _h_suggest_profile_updates,
    _h_summary,
    _h_sync_github,
    _h_sync_linkedin_brightdata,
    _h_sync_linkedin_dma,
    _h_update_header,
    _make_add_handler,
    _make_delete_handler,
    _make_update_handler,
)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Any
    required_scope: str | None = None


# --- Universe deps (build once per call) ------------------------------------


# --- Registry ---------------------------------------------------------------


_ENTITY_SCHEMAS: dict[str, dict[str, Any]] = {
    "education": {
        "required": ["institution"],
        "properties": {
            "institution": {"type": "string"},
            "degree": {"type": "string"},
            "field_of_study": {"type": "string"},
            "start_date": {"type": "string", "format": "date"},
            "end_date": {"type": "string", "format": "date"},
            "is_current": {"type": "boolean"},
            "description": {"type": "string"},
            "highlights": {"type": "array", "items": {"type": "string"}},
            "gpa": {"type": "number"},
            "url": {"type": "string"},
        },
    },
    "experience": {
        "required": ["organization", "role"],
        "properties": {
            "organization": {"type": "string"},
            "role": {"type": "string"},
            "start_date": {"type": "string", "format": "date"},
            "end_date": {"type": "string", "format": "date"},
            "is_current": {"type": "boolean"},
            "modality": {"type": "string", "enum": ["remote", "hybrid", "onsite"]},
            "employment_type": {"type": "string"},
            "description": {"type": "string"},
            "highlights": {"type": "array", "items": {"type": "string"}},
            "competences": {"type": "array", "items": {"type": "string"}},
        },
    },
    "project": {
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "start_date": {"type": "string", "format": "date"},
            "end_date": {"type": "string", "format": "date"},
            "is_current": {"type": "boolean"},
            "role": {"type": "string"},
            "project_type": {"type": "string", "enum": ["side", "oss", "entrepreneurship", "work"]},
            "tech_stack": {"type": "array", "items": {"type": "string"}},
            "highlights": {"type": "array", "items": {"type": "string"}},
            "impact": {"type": "string"},
            "url": {"type": "string"},
        },
    },
    "skill": {
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "category": {"type": "string", "enum": ["hard", "soft", "tool", "methodology"]},
            "level": {"type": "string", "enum": ["basic", "intermediate", "high", "expert"]},
            "years": {"type": "integer"},
            "last_used_year": {"type": "integer"},
        },
    },
    "certification": {
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "issuer": {"type": "string"},
            "issued_on": {"type": "string", "format": "date"},
            "expires_on": {"type": "string", "format": "date"},
            "credential_id": {"type": "string"},
            "verification_url": {"type": "string"},
        },
    },
    "course": {
        "required": ["title"],
        "properties": {
            "title": {"type": "string"},
            "platform": {"type": "string"},
            "started_on": {"type": "string", "format": "date"},
            "completed_on": {"type": "string", "format": "date"},
            "duration_hours": {"type": "integer"},
            "certificate_url": {"type": "string"},
        },
    },
    "language": {
        "required": ["code", "name", "level"],
        "properties": {
            "code": {"type": "string", "minLength": 2, "maxLength": 2},
            "name": {"type": "string"},
            "level": {"type": "string", "enum": ["A1", "A2", "B1", "B2", "C1", "C2", "native"]},
            "certification": {"type": "string"},
        },
    },
    "achievement": {
        "required": ["title"],
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "achieved_on": {"type": "string", "format": "date"},
            "context": {"type": "string"},
            "evidence_url": {"type": "string"},
        },
    },
    "interest": {
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
        },
    },
}


def _build_entity_tools() -> dict[str, ToolSpec]:
    out: dict[str, ToolSpec] = {}
    update_id_prop = {"id": {"type": "string", "format": "uuid"}}
    for entity, schema in _ENTITY_SCHEMAS.items():
        out[f"add_{entity}"] = ToolSpec(
            name=f"add_{entity}",
            description=f"Add an {entity} entry to the user's professional universe.",
            input_schema={
                "type": "object",
                "required": schema["required"],
                "properties": schema["properties"],
            },
            handler=_make_add_handler(entity),
            required_scope="universe:write",
        )
        out[f"update_{entity}"] = ToolSpec(
            name=f"update_{entity}",
            description=f"Patch an existing {entity} by id.",
            input_schema={
                "type": "object",
                "required": ["id"],
                "properties": {**update_id_prop, **schema["properties"]},
                "additionalProperties": True,
            },
            handler=_make_update_handler(entity),
            required_scope="universe:write",
        )
        out[f"delete_{entity}"] = ToolSpec(
            name=f"delete_{entity}",
            description=f"Remove an {entity} from the universe.",
            input_schema={
                "type": "object",
                "required": ["id"],
                "properties": update_id_prop,
            },
            handler=_make_delete_handler(entity),
            required_scope="universe:delete",
        )
    return out


_OTHER_TOOLS: dict[str, ToolSpec] = {
    "get_profile": ToolSpec(
        name="get_profile",
        description="Get a section (or all) of the user's professional universe.",
        input_schema={
            "type": "object",
            "properties": {"section": {"type": "string", "enum": ["all", "education", "experience", "skill"], "default": "all"}},
        },
        handler=_h_get_profile,
        required_scope="universe:read",
    ),
    "get_universe_summary": ToolSpec(
        name="get_universe_summary",
        description="Compact summary: headline, counts, top skills, recent experiences, languages.",
        input_schema={"type": "object", "properties": {}},
        handler=_h_summary,
        required_scope="universe:read",
    ),
    "list_skills": ToolSpec(
        name="list_skills",
        description="List skills filtered by category / min level / min years.",
        input_schema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["hard", "soft", "tool", "methodology"]},
                "min_level": {"type": "string", "enum": ["basic", "intermediate", "high", "expert"]},
                "min_years": {"type": "integer"},
            },
        },
        handler=_h_list_skills,
        required_scope="universe:read",
    ),
    "search_universe": ToolSpec(
        name="search_universe",
        description="Semantic search across the user's universe.",
        input_schema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 10},
                "entity_types": {"type": "array", "items": {"type": "string"}},
            },
        },
        handler=_h_search,
        required_scope="universe:read",
    ),
    "set_career_preferences": ToolSpec(
        name="set_career_preferences",
        description="Set or patch career preferences (status, salary, modality, etc.).",
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "salary_min": {"type": "number"},
                "salary_max": {"type": "number"},
                "salary_currency": {"type": "string"},
                "contract_types": {"type": "array", "items": {"type": "string"}},
                "remote_preference": {"type": "string"},
                "open_to_relocate": {"type": "boolean"},
                "preferred_roles": {"type": "array", "items": {"type": "string"}},
                "discarded_roles": {"type": "array", "items": {"type": "string"}},
                "preferred_competences": {"type": "array", "items": {"type": "string"}},
                "discarded_competences": {"type": "array", "items": {"type": "string"}},
                "motivations": {"type": "string"},
            },
        },
        handler=_h_set_prefs,
        required_scope="preferences:write",
    ),
    "get_career_preferences": ToolSpec(
        name="get_career_preferences",
        description="Read current career preferences.",
        input_schema={"type": "object", "properties": {}},
        handler=_h_get_prefs,
        required_scope="preferences:read",
    ),
    "update_universe_header": ToolSpec(
        name="update_universe_header",
        description="Set headline, summary, current_status, photo URL.",
        input_schema={
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "summary": {"type": "string"},
                "photo_url": {"type": "string"},
                "current_status": {"type": "string"},
            },
        },
        handler=_h_update_header,
        required_scope="universe:write",
    ),
    "mark_reviewed": ToolSpec(
        name="mark_reviewed",
        description="Touch last_reviewed_at on an entity.",
        input_schema={
            "type": "object",
            "required": ["entity_type", "entity_id"],
            "properties": {
                "entity_type": {"type": "string"},
                "entity_id": {"type": "string", "format": "uuid"},
            },
        },
        handler=_h_mark_reviewed,
        required_scope="universe:write",
    ),
    "link_evidence": ToolSpec(
        name="link_evidence",
        description="Link a skill to an evidence entity (experience/project/etc).",
        input_schema={
            "type": "object",
            "required": ["skill_id", "evidence_entity_type", "evidence_entity_id"],
            "properties": {
                "skill_id": {"type": "string", "format": "uuid"},
                "evidence_entity_type": {"type": "string"},
                "evidence_entity_id": {"type": "string", "format": "uuid"},
                "weight": {"type": "number", "default": 1.0},
                "notes": {"type": "string"},
            },
        },
        handler=_h_link_evidence,
        required_scope="evidence:write",
    ),
    "get_activity": ToolSpec(
        name="get_activity",
        description="Return recent universe activity.",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 50},
                "since": {"type": "string", "format": "date-time"},
                "event_types": {"type": "array", "items": {"type": "string"}},
            },
        },
        handler=_h_get_activity,
        required_scope="universe:read",
    ),
    "match_job_to_profile": ToolSpec(
        name="match_job_to_profile",
        description="Score a JD against the user's universe.",
        input_schema={
            "type": "object",
            "properties": {
                "job_url": {"type": "string"},
                "job_description": {"type": "string"},
            },
        },
        handler=_h_match_job,
        required_scope="universe:read",
    ),
    "generate_cv": ToolSpec(
        name="generate_cv",
        description="Generate an ATS-adapted CV (PDF + DOCX + JSON Resume).",
        input_schema={
            "type": "object",
            "properties": {
                "job_url": {"type": "string"},
                "job_description": {"type": "string"},
                "template": {"type": "string", "default": "ats-classic"},
                "language": {"type": "string", "enum": ["es", "en"], "default": "es"},
                "tone": {"type": "string"},
                "length": {"type": "string", "enum": ["1-page", "2-page"]},
            },
        },
        handler=_h_generate_cv,
        required_scope="documents:generate",
    ),
    "list_documents": ToolSpec(
        name="list_documents",
        description="List generated CVs / cover letters.",
        input_schema={
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["cv", "cover_letter"]},
                "limit": {"type": "integer", "default": 20},
            },
        },
        handler=_h_list_documents,
        required_scope="documents:read",
    ),
    "get_document": ToolSpec(
        name="get_document",
        description="Get a single document by id.",
        input_schema={
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "string", "format": "uuid"}},
        },
        handler=_h_get_document,
        required_scope="documents:read",
    ),
    "share_document": ToolSpec(
        name="share_document",
        description="Create a public share token for a document.",
        input_schema={
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "expires_in_days": {"type": "integer", "default": 30},
            },
        },
        handler=_h_share_document,
        required_scope="documents:read",
    ),
    "list_connections": ToolSpec(
        name="list_connections",
        description="List external accounts connected to this universe.",
        input_schema={"type": "object", "properties": {}},
        handler=_h_list_connections,
        required_scope="integrations:read",
    ),
    "sync_github": ToolSpec(
        name="sync_github",
        description="Trigger an immediate GitHub sync.",
        input_schema={"type": "object", "properties": {"force_full": {"type": "boolean", "default": False}}},
        handler=_h_sync_github,
        required_scope="integrations:write",
    ),
    "disconnect_account": ToolSpec(
        name="disconnect_account",
        description="Disconnect an external account.",
        input_schema={
            "type": "object",
            "required": ["provider"],
            "properties": {"provider": {"type": "string"}},
        },
        handler=_h_disconnect_account,
        required_scope="integrations:write",
    ),
    "import_linkedin_zip": ToolSpec(
        name="import_linkedin_zip",
        description="Parse a LinkedIn data ZIP (base64) and optionally commit entities.",
        input_schema={
            "type": "object",
            "required": ["file_base64"],
            "properties": {
                "file_base64": {"type": "string"},
                "auto_commit": {"type": "boolean", "default": False},
            },
        },
        handler=_h_import_linkedin_zip,
        required_scope="universe:write",
    ),
    "import_pdf_cv": ToolSpec(
        name="import_pdf_cv",
        description="Parse a CV PDF (base64) into a structured payload (review before commit).",
        input_schema={
            "type": "object",
            "required": ["file_base64"],
            "properties": {"file_base64": {"type": "string"}},
        },
        handler=_h_import_pdf_cv,
        required_scope="universe:write",
    ),
    "suggest_profile_updates": ToolSpec(
        name="suggest_profile_updates",
        description="Generate fresh suggestions (skills to add, expiring certs, stale entries…).",
        input_schema={"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}},
        handler=_h_suggest_profile_updates,
        required_scope="suggestions:write",
    ),
    "list_suggestions": ToolSpec(
        name="list_suggestions",
        description="List pending suggestions.",
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "default": "pending"},
                "limit": {"type": "integer", "default": 50},
            },
        },
        handler=_h_list_suggestions,
        required_scope="suggestions:read",
    ),
    "apply_suggestion": ToolSpec(
        name="apply_suggestion",
        description="Accept or reject a suggestion.",
        input_schema={
            "type": "object",
            "required": ["suggestion_id", "action"],
            "properties": {
                "suggestion_id": {"type": "string", "format": "uuid"},
                "action": {"type": "string", "enum": ["accept", "reject"]},
            },
        },
        handler=_h_apply_suggestion,
        required_scope="suggestions:write",
    ),
    "list_reminders": ToolSpec(
        name="list_reminders",
        description="List active reminders.",
        input_schema={
            "type": "object",
            "properties": {"due_within_days": {"type": "integer"}},
        },
        handler=_h_list_reminders,
        required_scope="reminders:read",
    ),
    "dismiss_reminder": ToolSpec(
        name="dismiss_reminder",
        description="Dismiss a reminder.",
        input_schema={
            "type": "object",
            "required": ["reminder_id"],
            "properties": {"reminder_id": {"type": "string", "format": "uuid"}},
        },
        handler=_h_dismiss_reminder,
        required_scope="reminders:write",
    ),
    "scan_reminders": ToolSpec(
        name="scan_reminders",
        description="Run reminder scan (cert expiry, course stale, etc).",
        input_schema={"type": "object", "properties": {}},
        handler=_h_scan_reminders,
        required_scope="reminders:write",
    ),
    "set_avatar": ToolSpec(
        name="set_avatar",
        description="Upload profile photo (base64-encoded JPG/PNG/WebP, max 5 MB).",
        input_schema={
            "type": "object",
            "required": ["file_base64"],
            "properties": {
                "file_base64": {"type": "string"},
                "mime_type": {"type": "string"},
                "filename": {"type": "string"},
            },
        },
        handler=_h_set_avatar,
        required_scope="universe:write",
    ),
    "get_avatar_url": ToolSpec(
        name="get_avatar_url",
        description="Return the URL of the user's profile photo (or null).",
        input_schema={"type": "object", "properties": {}},
        handler=_h_get_avatar_url,
        required_scope="universe:read",
    ),
    "sync_linkedin_dma": ToolSpec(
        name="sync_linkedin_dma",
        description=(
            "Pull profile data via LinkedIn DMA 3rd-party API (EEA users, free) "
            "and open an import session. Returns the parsed payload — review and "
            "commit via `commit_import_session`. Uses a deterministic fixture in "
            "dev when `LINKEDIN_DMA_ENABLED=false`."
        ),
        input_schema={"type": "object", "properties": {}},
        handler=_h_sync_linkedin_dma,
        required_scope="integrations:write",
    ),
    "sync_linkedin_brightdata": ToolSpec(
        name="sync_linkedin_brightdata",
        description=(
            "Pull profile data via Bright Data LinkedIn People Profile API "
            "(global, paid). PRO tier required. Returns parsed payload — "
            "review and commit via `commit_import_session`. `fresh=true` "
            "forces a non-cached lookup (more expensive, ~$0.50-1)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "linkedin_url": {"type": "string", "description": "Public LinkedIn profile URL"},
                "fresh": {"type": "boolean", "default": False},
            },
        },
        handler=_h_sync_linkedin_brightdata,
        required_scope="integrations:write",
    ),
    "commit_import_session": ToolSpec(
        name="commit_import_session",
        description=(
            "Commit a previously-opened import session (linkedin_dma, "
            "linkedin_brightdata, linkedin_zip, pdf). Optional `selection` to "
            "commit only a subset of items per section."
        ),
        input_schema={
            "type": "object",
            "required": ["session_id"],
            "properties": {
                "session_id": {"type": "string", "format": "uuid"},
                "selection": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                },
            },
        },
        handler=_h_commit_import_session,
        required_scope="universe:write",
    ),
    "set_user_tier": ToolSpec(
        name="set_user_tier",
        description=(
            "Set the user's subscription tier (free | pro). In production this "
            "is driven by Stripe webhooks; today it's exposed for dev/admin use."
        ),
        input_schema={
            "type": "object",
            "required": ["tier"],
            "properties": {"tier": {"type": "string", "enum": ["free", "pro"]}},
        },
        handler=_h_set_user_tier,
        required_scope="account:write",
    ),
    "get_user_tier": ToolSpec(
        name="get_user_tier",
        description="Return current subscription tier.",
        input_schema={"type": "object", "properties": {}},
        handler=_h_get_user_tier,
        required_scope="account:read",
    ),
}


def _assemble_tools() -> dict[str, ToolSpec]:
    from src.shared.config import get_settings

    tools: dict[str, ToolSpec] = {**_build_entity_tools(), **_OTHER_TOOLS}
    # The set_user_tier dev/admin tool must never be reachable in production
    # (tier is Stripe-derived there); drop it from the registry entirely.
    if get_settings().is_prod:
        tools.pop("set_user_tier", None)
    return tools


TOOLS: dict[str, ToolSpec] = _assemble_tools()
