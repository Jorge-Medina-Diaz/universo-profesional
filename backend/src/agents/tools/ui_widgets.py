"""External-execution tools — generative UI cards shown in the chat.

Each `@tool(external_execution=True)` declares an argument schema. When the
model "calls" the tool, Agno emits an AG-UI tool-call event with those
arguments — execution happens in the React layer via `useCopilotAction`,
which renders a confirm/edit card and pipes the user's decision back as the
tool result. The Python body is never executed and exists only to give the
LLM a docstring + typed signature.

Tool names MUST match the names registered in `frontend/src/chat/actions.tsx`
(`useCopilotAction({ name: "propose_experience", ... })`).
"""
from __future__ import annotations

from typing import Any

from agno.tools import tool


def _client_only() -> Any:
    raise RuntimeError("This tool runs on the client UI, not the server.")


# --- Factory -----------------------------------------------------------------


def _make_tool(
    name: str,
    description: str,
    params: list[dict[str, Any]],
    doc: str | None = None,
) -> Any:
    """Dynamically create a client-only tool function with correct signature."""
    param_lines: list[str] = []
    for p in params:
        pname = p["name"]
        ptype = p["type"]
        default = p.get("default", ...)
        if default is not ...:
            param_lines.append(f"    {pname}: {ptype} = {default!r},")
        else:
            param_lines.append(f"    {pname}: {ptype},")

    params_str = "\n".join(param_lines) if param_lines else "    # no params"
    func_doc = doc if doc is not None else description

    src = f'''def {name}(
{params_str}
) -> str:
    """{func_doc}"""
    return _client_only()
'''

    local_ns: dict[str, Any] = {"_client_only": _client_only, "Any": Any}
    exec(src, local_ns)
    func = local_ns[name]
    func.__module__ = __name__
    return tool(name=name, description=description, external_execution=True)(func)


_HITL_TOOLS: list[dict[str, Any]] = [
    {
        "name": "propose_experience",
        "description": "Propose a work-experience entry. Card shows fields for confirm/edit/reject.",
        "params": [
            {"name": "organization", "type": "str"},
            {"name": "role", "type": "str"},
            {"name": "start_date", "type": "str | None", "default": None},
            {"name": "end_date", "type": "str | None", "default": None},
            {"name": "is_current", "type": "bool | None", "default": None},
            {"name": "description", "type": "str | None", "default": None},
            {"name": "highlights", "type": "list[str] | None", "default": None},
            {"name": "competences", "type": "list[str] | None", "default": None},
        ],
    },
    {
        "name": "propose_education",
        "description": "Propose an education entry (university, degree, dates, highlights).",
        "params": [
            {"name": "institution", "type": "str"},
            {"name": "degree", "type": "str | None", "default": None},
            {"name": "field_of_study", "type": "str | None", "default": None},
            {"name": "start_date", "type": "str | None", "default": None},
            {"name": "end_date", "type": "str | None", "default": None},
            {"name": "is_current", "type": "bool | None", "default": None},
            {"name": "description", "type": "str | None", "default": None},
            {"name": "highlights", "type": "list[str] | None", "default": None},
        ],
    },
    {
        "name": "propose_project",
        "description": "Propose a project entry (name, description, stack, highlights, impact).",
        "params": [
            {"name": "name", "type": "str"},
            {"name": "description", "type": "str | None", "default": None},
            {"name": "role", "type": "str | None", "default": None},
            {"name": "project_type", "type": "str | None", "default": None},
            {"name": "tech_stack", "type": "list[str] | None", "default": None},
            {"name": "highlights", "type": "list[str] | None", "default": None},
            {"name": "impact", "type": "str | None", "default": None},
            {"name": "url", "type": "str | None", "default": None},
            {"name": "is_current", "type": "bool | None", "default": None},
        ],
    },
    {
        "name": "propose_skill",
        "description": "Propose a skill entry (name, category=hard|soft|tool|methodology, level, years).",
        "params": [
            {"name": "name", "type": "str"},
            {"name": "category", "type": "str | None", "default": None},
            {"name": "level", "type": "str | None", "default": None},
            {"name": "years", "type": "int | None", "default": None},
            {"name": "last_used_year", "type": "int | None", "default": None},
        ],
    },
    {
        "name": "propose_certification",
        "description": "Propose a certification entry (name, issuer, dates, credential id).",
        "params": [
            {"name": "name", "type": "str"},
            {"name": "issuer", "type": "str | None", "default": None},
            {"name": "issued_on", "type": "str | None", "default": None},
            {"name": "expires_on", "type": "str | None", "default": None},
            {"name": "credential_id", "type": "str | None", "default": None},
            {"name": "verification_url", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_course",
        "description": "Propose a course entry (title, platform, dates, duration).",
        "params": [
            {"name": "title", "type": "str"},
            {"name": "platform", "type": "str | None", "default": None},
            {"name": "started_on", "type": "str | None", "default": None},
            {"name": "completed_on", "type": "str | None", "default": None},
            {"name": "duration_hours", "type": "int | None", "default": None},
            {"name": "certificate_url", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_language",
        "description": "Propose a language entry (ISO-639-1 code, name, CEFR level A1..C2).",
        "params": [
            {"name": "code", "type": "str"},
            {"name": "name", "type": "str"},
            {"name": "level", "type": "str"},
            {"name": "certification", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_achievement",
        "description": "Propose an achievement entry (title, date, context, evidence URL).",
        "params": [
            {"name": "title", "type": "str"},
            {"name": "achieved_on", "type": "str | None", "default": None},
            {"name": "description", "type": "str | None", "default": None},
            {"name": "context", "type": "str | None", "default": None},
            {"name": "evidence_url", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_artifact",
        "description": (
            "Propose a portfolio artifact (github_repo|talk|blog_post|oss_contrib|"
            "paper|podcast|video|book|other) for the user to confirm. Use when the "
            "user mentions a public repo, talk, post, OSS PR, paper, podcast or "
            "video tied to their work. Required: type, title, url. Optional: year, "
            "description, venue, linked_project_id. The card lets the user adjust "
            "details before persisting."
        ),
        "params": [
            {"name": "type", "type": "str"},
            {"name": "title", "type": "str"},
            {"name": "url", "type": "str"},
            {"name": "year", "type": "int | None", "default": None},
            {"name": "description", "type": "str | None", "default": None},
            {"name": "venue", "type": "str | None", "default": None},
            {"name": "linked_project_id", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_architecture_decision",
        "description": (
            "Propose an architecture decision record (ADR). Use when the user "
            "describes a deliberate decision they made about architecture "
            "(microservices vs monolith, event-driven vs request-response, "
            "vendor choice, language pick for a service, etc.). Required: title. "
            "Strongly recommended: context (why this came up), decision (what we "
            "picked), consequences (trade-offs accepted). Status defaults to "
            "'accepted'. Optionally link to a project via related_project_id."
        ),
        "params": [
            {"name": "title", "type": "str"},
            {"name": "context", "type": "str | None", "default": None},
            {"name": "decision", "type": "str | None", "default": None},
            {"name": "consequences", "type": "str | None", "default": None},
            {"name": "status", "type": "str | None", "default": None},
            {"name": "tags", "type": "list[str] | None", "default": None},
            {"name": "related_project_id", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_interest",
        "description": "Propose a personal/professional interest entry.",
        "params": [
            {"name": "name", "type": "str"},
            {"name": "description", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_entity",
        "description": (
            "GENERIC single-entity proposal (R13). Propose ONE professional "
            "entity of any supported kind in a single confirm/edit/reject card. "
            "`entity_type` MUST be one of: experience | education | project | "
            "skill | certification | course | language | achievement | interest "
            "| artifact | architecture_decision. `payload` is that kind's field "
            "dict — exactly the same shape as the matching `propose_<kind>` tool "
            "(e.g. experience → {organization, role, start_date, end_date, "
            "is_current, description, highlights, competences}; skill → {name, "
            "category, level, years}). Use for a SINGLE entity the user mentioned "
            "conversationally — for bulk/imported content use present_import_review."
        ),
        "doc": (
            "`entity_type`: one of the 11 supported universe kinds.\n"
            "`payload`: that kind's field dict (same shape as propose_<kind>)."
        ),
        "params": [
            {"name": "entity_type", "type": "str"},
            {"name": "payload", "type": "dict[str, Any]"},
        ],
    },
    {
        "name": "present_questionnaire",
        "description": (
            "Show the user a batch of 3-6 related questions in ONE card (onboarding, "
            "check-ins, enrichment after an import). Each question is an object: "
            "{id: str (stable, returned in answers), kind: 'single_choice'|"
            "'multi_choice'|'scale'|'open', prompt: str (the question text — use the "
            "key `prompt`)}. For single_choice/multi_choice you MUST include "
            "`options: string[]`. For scale add `scale_min`/`scale_max` (default "
            "1..5). MIX the kinds — don't make everything `open`: use multi_choice "
            "(with options) to let the user tick known technologies/skills, "
            "single_choice for one-of, scale for proficiency/seniority, and `open` "
            "only for genuinely free text (e.g. 'anything else?'). Prefer offering "
            "concrete options the user can tap over asking them to type."
        ),
        "params": [
            {"name": "title", "type": "str"},
            {"name": "questions", "type": "list[dict[str, Any]]"},
            {"name": "submit_label", "type": "str | None", "default": None},
            {"name": "intro", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "present_deep_dive",
        "description": (
            "Show a multi-section deep-dive card to gently extract structured info "
            "about a topic / domain the user is exploring. Use when the user says "
            "'estoy aprendiendo X', 'he estado investigando Y', 'he montado Z'. "
            "Each section MUST declare: id (str), title (str), kind (multi_chips | "
            "single_chips | chip_input | scale | open). For *_chips also include "
            "options (list[str]). For scale optionally scale_min / scale_max. "
            "Returns a JSON string with shape "
            "{topic: str, sections: {[sectionId]: value}} or the literal 'skipped' "
            "if the user dismissed the card."
        ),
        "params": [
            {"name": "title", "type": "str"},
            {"name": "domain", "type": "str"},
            {"name": "sections", "type": "list[dict[str, Any]]"},
            {"name": "intro", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_goal",
        "description": (
            "Show a confirmation card to add a new professional goal. Use when the "
            "user expresses a clear outcome they want to reach: 'quiero ser senior "
            "fullstack en 6 meses', 'me gustaría dar charlas técnicas', 'quiero "
            "pivotar a ML'. `horizon` MUST be one of '3_months' | '6_months' | "
            "'1_year' | 'long_term'. Optionally propose `subtasks` (3-5 concrete "
            "steps). User confirms before persistence."
        ),
        "params": [
            {"name": "title", "type": "str"},
            {"name": "horizon", "type": "str"},
            {"name": "description", "type": "str | None", "default": None},
            {"name": "target_date", "type": "str | None", "default": None},
            {"name": "subtasks", "type": "list[str] | None", "default": None},
        ],
    },
    {
        "name": "present_widget",
        "description": (
            "Push a display-only widget to the right-side widget pane so the user "
            "can browse structured data alongside the chat. Use after a read-only "
            "MCP / universe tool: pass `kind` + a short `title` + the `data` "
            "payload the widget will render. Supported kinds (13): "
            "job_match | document_preview | goals_progress | "
            "interview_qa | tech_radar | agent_patterns | signal_coverage | "
            "cloud_coverage | data_stack_topology | security_posture | "
            "architecture_patterns | portfolio_radar | learning_trajectory. "
            "For showing the user's universe as a navigable graph, prefer "
            "`present_graph_view` instead."
        ),
        "params": [
            {"name": "kind", "type": "str"},
            {"name": "title", "type": "str"},
            {"name": "data", "type": "dict[str, Any]"},
        ],
    },
    {
        "name": "present_graph_view",
        "description": (
            "Drive the navigable graph lens of the user's universe. Use this to "
            "show relationships rather than flat lists. Modes: "
            "'focus' (radius around `focus_entity_id`, default depth 2), "
            "'cluster' (Leiden communities / full graph with level-of-detail), "
            "'timeline' (episodes + temporal edges), "
            "'ontology_overlay' (ESCO concepts linked to the user's entities). "
            "Pass `focus_entity_id` for 'focus' mode (the entity_id returned by "
            "`universe_retrieve`). The frontend switches the /universe + chat "
            "graph lens to the requested mode."
        ),
        "params": [
            {"name": "mode", "type": "str"},
            {"name": "focus_entity_id", "type": "str | None", "default": None},
            {"name": "depth", "type": "int", "default": 2},
        ],
    },
    {
        "name": "propose_skill_batch",
        "description": (
            "Propose MULTIPLE related skills at once in a single card, so the user "
            "can confirm them as a batch (toggle per chip + tune level inline). "
            "Use this when the user mentions a tech stack or a set of competences "
            "in one breath (e.g. 'sé python, fastapi, react, docker y typescript'). "
            "Preferred over emitting N separate `propose_skill` tool calls. "
            "Each `skills` item: {name: str (required), category?: 'hard'|'soft'|'tool'|'methodology', "
            "level?: 'basic'|'intermediate'|'high'|'expert', years?: int}. "
            "Returns {accepted: SkillProposal[], rejected: string[]}."
        ),
        "params": [
            {"name": "skills", "type": "list[dict[str, Any]]"},
            {"name": "title", "type": "str | None", "default": None},
            {"name": "intro", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_cover_letter",
        "description": (
            "Offer the user to generate a cover letter for a job description. Use "
            "when the user has pasted a JD in chat or asked explicitly for a cover "
            "letter. The card confirms and opens the CV generator pre-filled with "
            "the JD and `kind=cover_letter` selected."
        ),
        "params": [
            {"name": "job_description", "type": "str"},
            {"name": "job_url", "type": "str | None", "default": None},
            {"name": "company", "type": "str | None", "default": None},
            {"name": "title", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_document_generation",
        "description": (
            "Offer the user to generate a NEW document (CV or cover letter) after "
            "the conversational discovery is complete. The card shows a summary of "
            "the choices (kind, template, tone, language, target job if any) and "
            "opens the generator pre-filled with those settings. Use ONLY after "
            "you have gathered: document kind, tone preference, and optionally a "
            "job description."
        ),
        "params": [
            {"name": "kind", "type": "str"},
            {"name": "template", "type": "str"},
            {"name": "tone", "type": "str"},
            {"name": "language", "type": "str", "default": "es"},
            {"name": "job_description", "type": "str | None", "default": None},
            {"name": "job_url", "type": "str | None", "default": None},
            {"name": "job_title", "type": "str | None", "default": None},
            {"name": "company", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "present_job_match",
        "description": (
            "Render a visual match scorecard for a job description against the "
            "user's universe. Use AFTER running `match_job_to_profile` (server-side "
            "tool that computes the score, strengths, gaps and suggested ATS "
            "keywords). Display-only — does not require the user to confirm; they "
            "may tap 'Generate CV' which opens the generator pre-filled."
        ),
        "params": [
            {"name": "match_score", "type": "int"},
            {"name": "strengths", "type": "list[str] | None", "default": None},
            {"name": "gaps", "type": "list[str] | None", "default": None},
            {"name": "suggested_keywords", "type": "list[str] | None", "default": None},
            {"name": "job_title", "type": "str | None", "default": None},
            {"name": "company", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_github_sync",
        "description": "Ask the user to confirm pulling their GitHub profile (repos, languages, pinned).",
        "params": [],
    },
    {
        "name": "propose_brightdata_sync",
        "description": "Ask the user to confirm a Bright Data LinkedIn sync (PRO tier only).",
        "params": [],
    },
    {
        "name": "propose_pdf_import",
        "description": "Ask the user to upload a CV PDF and confirm which entries to import.",
        "params": [],
    },
    {
        "name": "present_import_review",
        "description": (
            "Show ONE batch-review card for a whole ingestion (an attached/pasted CV, "
            "a LinkedIn dump, or a block of facts the user dictated). This is the "
            "ONLY way to capture an import — NEVER drip one `propose_*` card per "
            "entity for imported content. Imported/dictated content is TRUSTED: the "
            "card defaults every item to selected; the user reviews the whole set at "
            "once and may deselect or tweak parts before committing them together. "
            "`groups` is a list of {kind, items}: kind ∈ experience|education|project|"
            "skill|certification|course|language|achievement|interest|artifact; each "
            "item is the same payload shape as the matching `propose_*`/`upsert_*` "
            "tool (e.g. experience → {organization, role, start_date, end_date, "
            "is_current, description, highlights, competences}). Extract EVERYTHING "
            "you can from the source into the right groups. Returns "
            "{committed: {<kind>: count}, total: int} after the user confirms — then "
            "summarise briefly and move on to enrichment (do not re-propose what was "
            "imported)."
        ),
        "doc": (
            "`groups`: [{kind: str, items: [ {<entity payload>}, ... ]}, ...].\n\n"
            "The card commits every selected item through the coherence engine (which\n"
            "dedups/merges against what already exists), so re-importing is safe."
        ),
        "params": [
            {"name": "groups", "type": "list[dict[str, Any]]"},
            {"name": "title", "type": "str | None", "default": None},
            {"name": "source", "type": "str | None", "default": None},
            {"name": "intro", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "select_job_from_list",
        "description": (
            "Show the user a list of their jobs (kanban entries) and let them pick "
            "ONE. Use after `list_jobs` when the next step needs a specific job "
            "(generate CV for it, recompute match, change status, etc.). "
            "`items` is the list of jobs to show (same shape as `list_jobs` "
            "returns: id, title, company_name, status, match_score, …). "
            "`prompt` is the question to display. Returns the selected job id "
            "or null if the user cancels."
        ),
        "params": [
            {"name": "items", "type": "list[dict[str, Any]]"},
            {"name": "prompt", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "select_document_from_list",
        "description": (
            "Show the user a list of their generated documents and let them pick "
            "ONE. Use after `list_documents` when the next step needs a specific "
            "document (regenerate, compare, share, etc.). `items` shape matches "
            "`list_documents` output. Returns the selected document id or null."
        ),
        "params": [
            {"name": "items", "type": "list[dict[str, Any]]"},
            {"name": "prompt", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "preview_list",
        "description": (
            "Display-only list of items as cards in the chat. Use to surface "
            "context (your 3 most relevant jobs, your last 5 documents, pending "
            "reminders) without asking the user to pick — just a visual snapshot "
            "with click-through CTAs. `kind` declares the visual treatment: "
            "'jobs' | 'documents' | 'reminders' | 'integrations'. `items` shape "
            "matches the corresponding list_* tool. `title` is shown as the "
            "card header."
        ),
        "params": [
            {"name": "kind", "type": "str"},
            {"name": "items", "type": "list[dict[str, Any]]"},
            {"name": "title", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_job_create",
        "description": (
            "Propose creating a new job tracker entry from a JD the user pasted "
            "(or details they described). The card lets them edit title, company, "
            "URL and description before saving. Use when the user describes an "
            "offer that should land in the kanban."
        ),
        "params": [
            {"name": "title", "type": "str | None", "default": None},
            {"name": "company_name", "type": "str | None", "default": None},
            {"name": "url", "type": "str | None", "default": None},
            {"name": "description_raw", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_job_status_change",
        "description": (
            "Propose moving a job to a different status (kanban transition). "
            "`new_status` must be one of: interested, applied, interviewing, "
            "offer, rejected, archived. The card shows a confirm dialog with "
            "the current vs new status."
        ),
        "params": [
            {"name": "job_id", "type": "str"},
            {"name": "new_status", "type": "str"},
            {"name": "job_title", "type": "str | None", "default": None},
            {"name": "company", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_autopilot_run",
        "description": (
            "Propose running the autopilot flow for a specific job: generate CV "
            "+ cover letter + mark as applied. The card lets the user confirm "
            "template / language / tone before starting. Use after the user "
            "asks to apply to a job."
        ),
        "params": [
            {"name": "job_id", "type": "str"},
            {"name": "job_title", "type": "str | None", "default": None},
            {"name": "company", "type": "str | None", "default": None},
            {"name": "suggested_template", "type": "str | None", "default": None},
            {"name": "suggested_language", "type": "str | None", "default": None},
            {"name": "suggested_tone", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_cv_regenerate",
        "description": (
            "Propose regenerating an existing document with new settings (different "
            "template, language, tone). The card shows a side-by-side of current "
            "vs new settings and confirms the action. Use when the cv_coach "
            "recommends a different version."
        ),
        "params": [
            {"name": "document_id", "type": "str"},
            {"name": "template_override", "type": "str | None", "default": None},
            {"name": "language_override", "type": "str | None", "default": None},
            {"name": "tone_override", "type": "str | None", "default": None},
            {"name": "rationale", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_preferences_update",
        "description": (
            "Propose patching the user's career preferences. `patch` is the dict "
            "of fields to update (same schema as `update_preferences`). The card "
            "shows old → new for each field. Use granular patches (1-3 fields at "
            "a time) so the user can accept/reject parts."
        ),
        "params": [
            {"name": "patch", "type": "dict[str, Any]"},
            {"name": "rationale", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "confirm_destructive",
        "description": (
            "Generic HITL confirmation gate for any action that the user should "
            "explicitly approve before it runs — typically deletes, mass "
            "operations, status flips, etc. `action_label` is the verb ('Eliminar', "
            "'Archivar'); `target` describes what's affected; `payload` is a "
            "structured detail the card renders. Returns {confirmed: bool}."
        ),
        "params": [
            {"name": "action_label", "type": "str"},
            {"name": "target", "type": "str"},
            {"name": "payload", "type": "dict[str, Any] | None", "default": None},
            {"name": "tone", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "present_document_preview",
        "description": (
            "Render an inline preview of a generated document (CV or cover letter) "
            "with collapsible sections (summary / experience / skills / cover body). "
            "Display-only — no confirmation needed. Pass `document_id`. Optional "
            "`offer_regenerate=true` adds a 'Regenerar' CTA so the user can jump "
            "to the generator pre-filled. Optional `offer_variant=true` adds a "
            "'Generar variante' CTA (e.g. a version tailored to another job)."
        ),
        "params": [
            {"name": "document_id", "type": "str"},
            {"name": "offer_regenerate", "type": "bool | None", "default": None},
            {"name": "offer_variant", "type": "bool | None", "default": None},
        ],
    },
    {
        "name": "present_progress",
        "description": (
            "Display-only progress card for a long-running task. Pass `title`, "
            "`state` ('running' | 'done' | 'error'), `steps` (list of "
            "{id, label, status: 'pending' | 'active' | 'done' | 'error'}), and "
            "optional `detail` / `error_message`. Sprint B scope: static — the "
            "agent emits a new card per step. Sprint C will pipe live events."
        ),
        "params": [
            {"name": "title", "type": "str"},
            {"name": "state", "type": "str"},
            {"name": "steps", "type": "list[dict[str, Any]]"},
            {"name": "detail", "type": "str | None", "default": None},
            {"name": "error_message", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "set_chat_focus",
        "description": (
            "Signal to the frontend which entity you are currently reasoning "
            "about, so other pages can highlight / scroll-to / pre-select it. "
            "`entity` is one of: 'job' | 'document' | 'note' | 'experience' | "
            "'education' | 'project' | 'skill' | 'certification' | 'course' | "
            "'language' | 'achievement' | 'interest'. `id` is the entity uuid. "
            "`meta` is an optional dict the frontend may use to render contextual "
            "hints (e.g. {next_action: 'autopilot'}). No confirmation needed — "
            "fires and resolves immediately. Use sparingly: only when narrowing "
            "the conversation to a specific entity helps the user."
        ),
        "params": [
            {"name": "entity", "type": "str"},
            {"name": "id", "type": "str"},
            {"name": "meta", "type": "dict[str, Any] | None", "default": None},
        ],
    },
    {
        "name": "upload_document_inline",
        "description": (
            "Open an inline upload dropzone in the chat so the user can drop a "
            "PDF or image without leaving the conversation. `accept` is the MIME "
            "list ('application/pdf', 'image/*', …); `purpose` is a short label "
            "shown to the user ('Importar tu CV', 'Foto de perfil'). Returns "
            "{uploaded: bool, file_url: string?, kind: 'pdf'|'image'|'other'}."
        ),
        "params": [
            {"name": "purpose", "type": "str"},
            {"name": "accept", "type": "str", "default": "application/pdf"},
            {"name": "max_bytes", "type": "int", "default": 10 * 1024 * 1024},
        ],
    },
    {
        "name": "propose_esco_disambiguation",
        "description": (
            "Ask the user to confirm which ESCO concept their entity refers to. "
            "Use this when the ESCO entity linker returns SUGGESTED — the personal "
            "skill / occupation could not be auto-linked with high enough confidence. "
            "Returns {chosen_uri: string?, dismissed: bool}; backend then attaches "
            "the LINKS_TO_ESCO edge if a URI was chosen."
        ),
        "doc": (
            "`candidates` is a list of {uri, label, pref_label_es, pref_label_en, score}.\n"
            "The user picks one or dismisses; the resolver endpoint persists the choice."
        ),
        "params": [
            {"name": "quarantine_id", "type": "str"},
            {"name": "entity_kind", "type": "str"},
            {"name": "entity_label", "type": "str"},
            {"name": "candidates", "type": "list[dict[str, Any]]"},
        ],
    },
    {
        "name": "propose_edge_creation",
        "description": (
            "Propose creating a typed edge between two existing entities in the "
            "user's graph (e.g. link a skill to a project, mark an ADR as part_of "
            "a project). Returns {accepted: bool}; backend creates the edge if "
            "accepted."
        ),
        "params": [
            {"name": "source_entity_id", "type": "str"},
            {"name": "source_label", "type": "str"},
            {"name": "target_entity_id", "type": "str"},
            {"name": "target_label", "type": "str"},
            {"name": "edge_type", "type": "str"},
            {"name": "rationale", "type": "str | None", "default": None},
        ],
    },
    {
        "name": "propose_edge_deletion",
        "description": (
            "Propose expiring (soft-deleting) an existing typed edge. Useful when "
            "the user says 'I'm not using X anymore' and the agent wants to mark "
            "the corresponding USES_TECH edge with valid_to=now()."
        ),
        "params": [
            {"name": "source_entity_id", "type": "str"},
            {"name": "target_entity_id", "type": "str"},
            {"name": "edge_type", "type": "str"},
            {"name": "rationale", "type": "str | None", "default": None},
        ],
    },
]

for _spec in _HITL_TOOLS:
    globals()[_spec["name"]] = _make_tool(**_spec)


# Aggregated list — handy for specialists that want "all entity proposals"
ALL_PROPOSE_TOOLS = [
    propose_experience,
    propose_education,
    propose_project,
    propose_skill,
    propose_certification,
    propose_course,
    propose_language,
    propose_achievement,
    propose_interest,
]


# All generic A2UI tools — convenient bundle for the coordinator and the two
# proactive specialists (job_strategist, cv_coach).
ALL_GENERIC_A2UI_TOOLS = [
    select_job_from_list,
    select_document_from_list,
    preview_list,
    propose_job_create,
    propose_job_status_change,
    propose_autopilot_run,
    propose_cv_regenerate,
    propose_preferences_update,
    confirm_destructive,
    upload_document_inline,
    present_document_preview,
    present_progress,
    set_chat_focus,
]
