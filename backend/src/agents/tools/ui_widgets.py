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


# --- Per-entity HITL cards --------------------------------------------------


@tool(
    name="propose_experience",
    description="Propose a work-experience entry. Card shows fields for confirm/edit/reject.",
    external_execution=True,
)
def propose_experience(
    organization: str,
    role: str,
    start_date: str | None = None,
    end_date: str | None = None,
    is_current: bool | None = None,
    description: str | None = None,
    highlights: list[str] | None = None,
    competences: list[str] | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_education",
    description="Propose an education entry (university, degree, dates, highlights).",
    external_execution=True,
)
def propose_education(
    institution: str,
    degree: str | None = None,
    field_of_study: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    is_current: bool | None = None,
    description: str | None = None,
    highlights: list[str] | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_project",
    description="Propose a project entry (name, description, stack, highlights, impact).",
    external_execution=True,
)
def propose_project(
    name: str,
    description: str | None = None,
    role: str | None = None,
    project_type: str | None = None,
    tech_stack: list[str] | None = None,
    highlights: list[str] | None = None,
    impact: str | None = None,
    url: str | None = None,
    is_current: bool | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_skill",
    description="Propose a skill entry (name, category=hard|soft|tool|methodology, level, years).",
    external_execution=True,
)
def propose_skill(
    name: str,
    category: str | None = None,
    level: str | None = None,
    years: int | None = None,
    last_used_year: int | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_certification",
    description="Propose a certification entry (name, issuer, dates, credential id).",
    external_execution=True,
)
def propose_certification(
    name: str,
    issuer: str | None = None,
    issued_on: str | None = None,
    expires_on: str | None = None,
    credential_id: str | None = None,
    verification_url: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_course",
    description="Propose a course entry (title, platform, dates, duration).",
    external_execution=True,
)
def propose_course(
    title: str,
    platform: str | None = None,
    started_on: str | None = None,
    completed_on: str | None = None,
    duration_hours: int | None = None,
    certificate_url: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_language",
    description="Propose a language entry (ISO-639-1 code, name, CEFR level A1..C2).",
    external_execution=True,
)
def propose_language(
    code: str,
    name: str,
    level: str,
    certification: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_achievement",
    description="Propose an achievement entry (title, date, context, evidence URL).",
    external_execution=True,
)
def propose_achievement(
    title: str,
    achieved_on: str | None = None,
    description: str | None = None,
    context: str | None = None,
    evidence_url: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_artifact",
    description=(
        "Propose a portfolio artifact (github_repo|talk|blog_post|oss_contrib|"
        "paper|podcast|video|book|other) for the user to confirm. Use when the "
        "user mentions a public repo, talk, post, OSS PR, paper, podcast or "
        "video tied to their work. Required: type, title, url. Optional: year, "
        "description, venue, linked_project_id. The card lets the user adjust "
        "details before persisting."
    ),
    external_execution=True,
)
def propose_artifact(
    type: str,
    title: str,
    url: str,
    year: int | None = None,
    description: str | None = None,
    venue: str | None = None,
    linked_project_id: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_architecture_decision",
    description=(
        "Propose an architecture decision record (ADR). Use when the user "
        "describes a deliberate decision they made about architecture "
        "(microservices vs monolith, event-driven vs request-response, "
        "vendor choice, language pick for a service, etc.). Required: title. "
        "Strongly recommended: context (why this came up), decision (what we "
        "picked), consequences (trade-offs accepted). Status defaults to "
        "'accepted'. Optionally link to a project via related_project_id."
    ),
    external_execution=True,
)
def propose_architecture_decision(
    title: str,
    context: str | None = None,
    decision: str | None = None,
    consequences: str | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
    related_project_id: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_interest",
    description="Propose a personal/professional interest entry.",
    external_execution=True,
)
def propose_interest(
    name: str,
    description: str | None = None,
) -> str:
    return _client_only()


# --- Batch questionnaires (A2UI-style) --------------------------------------


@tool(
    name="present_questionnaire",
    description=(
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
    external_execution=True,
)
def present_questionnaire(
    title: str,
    questions: list[dict[str, Any]],
    submit_label: str | None = None,
    intro: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="present_deep_dive",
    description=(
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
    external_execution=True,
)
def present_deep_dive(
    title: str,
    domain: str,
    sections: list[dict[str, Any]],
    intro: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_goal",
    description=(
        "Show a confirmation card to add a new professional goal. Use when the "
        "user expresses a clear outcome they want to reach: 'quiero ser senior "
        "fullstack en 6 meses', 'me gustaría dar charlas técnicas', 'quiero "
        "pivotar a ML'. `horizon` MUST be one of '3_months' | '6_months' | "
        "'1_year' | 'long_term'. Optionally propose `subtasks` (3-5 concrete "
        "steps). User confirms before persistence."
    ),
    external_execution=True,
)
def propose_goal(
    title: str,
    horizon: str,
    description: str | None = None,
    target_date: str | None = None,
    subtasks: list[str] | None = None,
) -> str:
    return _client_only()


@tool(
    name="present_widget",
    description=(
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
    external_execution=True,
)
def present_widget(
    kind: str,
    title: str,
    data: dict[str, Any],
) -> str:
    return _client_only()


@tool(
    name="present_graph_view",
    description=(
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
    external_execution=True,
)
def present_graph_view(
    mode: str,
    focus_entity_id: str | None = None,
    depth: int = 2,
) -> str:
    return _client_only()


@tool(
    name="propose_skill_batch",
    description=(
        "Propose MULTIPLE related skills at once in a single card, so the user "
        "can confirm them as a batch (toggle per chip + tune level inline). "
        "Use this when the user mentions a tech stack or a set of competences "
        "in one breath (e.g. 'sé python, fastapi, react, docker y typescript'). "
        "Preferred over emitting N separate `propose_skill` tool calls. "
        "Each `skills` item: {name: str (required), category?: 'hard'|'soft'|'tool'|'methodology', "
        "level?: 'basic'|'intermediate'|'high'|'expert', years?: int}. "
        "Returns {accepted: SkillProposal[], rejected: string[]}."
    ),
    external_execution=True,
)
def propose_skill_batch(
    skills: list[dict[str, Any]],
    title: str | None = None,
    intro: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_cover_letter",
    description=(
        "Offer the user to generate a cover letter for a job description. Use "
        "when the user has pasted a JD in chat or asked explicitly for a cover "
        "letter. The card confirms and opens the CV generator pre-filled with "
        "the JD and `kind=cover_letter` selected."
    ),
    external_execution=True,
)
def propose_cover_letter(
    job_description: str,
    job_url: str | None = None,
    company: str | None = None,
    title: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_document_generation",
    description=(
        "Offer the user to generate a NEW document (CV or cover letter) after "
        "the conversational discovery is complete. The card shows a summary of "
        "the choices (kind, template, tone, language, target job if any) and "
        "opens the generator pre-filled with those settings. Use ONLY after "
        "you have gathered: document kind, tone preference, and optionally a "
        "job description."
    ),
    external_execution=True,
)
def propose_document_generation(
    kind: str,
    template: str,
    tone: str,
    language: str = "es",
    job_description: str | None = None,
    job_url: str | None = None,
    job_title: str | None = None,
    company: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="present_job_match",
    description=(
        "Render a visual match scorecard for a job description against the "
        "user's universe. Use AFTER running `match_job_to_profile` (server-side "
        "tool that computes the score, strengths, gaps and suggested ATS "
        "keywords). Display-only — does not require the user to confirm; they "
        "may tap 'Generate CV' which opens the generator pre-filled."
    ),
    external_execution=True,
)
def present_job_match(
    match_score: int,
    strengths: list[str] | None = None,
    gaps: list[str] | None = None,
    suggested_keywords: list[str] | None = None,
    job_title: str | None = None,
    company: str | None = None,
) -> str:
    return _client_only()


# --- Import / sync proposals (HITL gate before heavy operations) ------------


@tool(
    name="propose_github_sync",
    description="Ask the user to confirm pulling their GitHub profile (repos, languages, pinned).",
    external_execution=True,
)
def propose_github_sync() -> str:
    return _client_only()


@tool(
    name="propose_brightdata_sync",
    description="Ask the user to confirm a Bright Data LinkedIn sync (PRO tier only).",
    external_execution=True,
)
def propose_brightdata_sync() -> str:
    return _client_only()


@tool(
    name="propose_pdf_import",
    description="Ask the user to upload a CV PDF and confirm which entries to import.",
    external_execution=True,
)
def propose_pdf_import() -> str:
    return _client_only()


@tool(
    name="present_import_review",
    description=(
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
    external_execution=True,
)
def present_import_review(
    groups: list[dict[str, Any]],
    title: str | None = None,
    source: str | None = None,
    intro: str | None = None,
) -> str:
    """`groups`: [{kind: str, items: [ {<entity payload>}, ... ]}, ...].

    The card commits every selected item through the coherence engine (which
    dedups/merges against what already exists), so re-importing is safe.
    """
    return _client_only()


# --- Generic A2UI cards (selectors, list previews, confirm, progress, upload) --
# These power the "100% chat-driven" experience: anything the user can do
# navigating between pages should also be doable inside the chat through
# these primitives.


@tool(
    name="select_job_from_list",
    description=(
        "Show the user a list of their jobs (kanban entries) and let them pick "
        "ONE. Use after `list_jobs` when the next step needs a specific job "
        "(generate CV for it, recompute match, change status, etc.). "
        "`items` is the list of jobs to show (same shape as `list_jobs` "
        "returns: id, title, company_name, status, match_score, …). "
        "`prompt` is the question to display. Returns the selected job id "
        "or null if the user cancels."
    ),
    external_execution=True,
)
def select_job_from_list(
    items: list[dict[str, Any]],
    prompt: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="select_document_from_list",
    description=(
        "Show the user a list of their generated documents and let them pick "
        "ONE. Use after `list_documents` when the next step needs a specific "
        "document (regenerate, compare, share, etc.). `items` shape matches "
        "`list_documents` output. Returns the selected document id or null."
    ),
    external_execution=True,
)
def select_document_from_list(
    items: list[dict[str, Any]],
    prompt: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="preview_list",
    description=(
        "Display-only list of items as cards in the chat. Use to surface "
        "context (your 3 most relevant jobs, your last 5 documents, pending "
        "reminders) without asking the user to pick — just a visual snapshot "
        "with click-through CTAs. `kind` declares the visual treatment: "
        "'jobs' | 'documents' | 'reminders' | 'integrations'. `items` shape "
        "matches the corresponding list_* tool. `title` is shown as the "
        "card header."
    ),
    external_execution=True,
)
def preview_list(
    kind: str,
    items: list[dict[str, Any]],
    title: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_job_create",
    description=(
        "Propose creating a new job tracker entry from a JD the user pasted "
        "(or details they described). The card lets them edit title, company, "
        "URL and description before saving. Use when the user describes an "
        "offer that should land in the kanban."
    ),
    external_execution=True,
)
def propose_job_create(
    title: str | None = None,
    company_name: str | None = None,
    url: str | None = None,
    description_raw: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_job_status_change",
    description=(
        "Propose moving a job to a different status (kanban transition). "
        "`new_status` must be one of: interested, applied, interviewing, "
        "offer, rejected, archived. The card shows a confirm dialog with "
        "the current vs new status."
    ),
    external_execution=True,
)
def propose_job_status_change(
    job_id: str,
    new_status: str,
    job_title: str | None = None,
    company: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_autopilot_run",
    description=(
        "Propose running the autopilot flow for a specific job: generate CV "
        "+ cover letter + mark as applied. The card lets the user confirm "
        "template / language / tone before starting. Use after the user "
        "asks to apply to a job."
    ),
    external_execution=True,
)
def propose_autopilot_run(
    job_id: str,
    job_title: str | None = None,
    company: str | None = None,
    suggested_template: str | None = None,
    suggested_language: str | None = None,
    suggested_tone: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_cv_regenerate",
    description=(
        "Propose regenerating an existing document with new settings (different "
        "template, language, tone). The card shows a side-by-side of current "
        "vs new settings and confirms the action. Use when the cv_coach "
        "recommends a different version."
    ),
    external_execution=True,
)
def propose_cv_regenerate(
    document_id: str,
    template_override: str | None = None,
    language_override: str | None = None,
    tone_override: str | None = None,
    rationale: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_preferences_update",
    description=(
        "Propose patching the user's career preferences. `patch` is the dict "
        "of fields to update (same schema as `update_preferences`). The card "
        "shows old → new for each field. Use granular patches (1-3 fields at "
        "a time) so the user can accept/reject parts."
    ),
    external_execution=True,
)
def propose_preferences_update(
    patch: dict[str, Any],
    rationale: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="confirm_destructive",
    description=(
        "Generic HITL confirmation gate for any action that the user should "
        "explicitly approve before it runs — typically deletes, mass "
        "operations, status flips, etc. `action_label` is the verb ('Eliminar', "
        "'Archivar'); `target` describes what's affected; `payload` is a "
        "structured detail the card renders. Returns {confirmed: bool}."
    ),
    external_execution=True,
)
def confirm_destructive(
    action_label: str,
    target: str,
    payload: dict[str, Any] | None = None,
    tone: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="present_document_preview",
    description=(
        "Render an inline preview of a generated document (CV or cover letter) "
        "with collapsible sections (summary / experience / skills / cover body). "
        "Display-only — no confirmation needed. Pass `document_id`. Optional "
        "`offer_regenerate=true` adds a 'Regenerar' CTA so the user can jump "
        "to the generator pre-filled."
    ),
    external_execution=True,
)
def present_document_preview(
    document_id: str,
    offer_regenerate: bool | None = None,
) -> str:
    return _client_only()


@tool(
    name="present_progress",
    description=(
        "Display-only progress card for a long-running task. Pass `title`, "
        "`state` ('running' | 'done' | 'error'), `steps` (list of "
        "{id, label, status: 'pending' | 'active' | 'done' | 'error'}), and "
        "optional `detail` / `error_message`. Sprint B scope: static — the "
        "agent emits a new card per step. Sprint C will pipe live events."
    ),
    external_execution=True,
)
def present_progress(
    title: str,
    state: str,
    steps: list[dict[str, Any]],
    detail: str | None = None,
    error_message: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="set_chat_focus",
    description=(
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
    external_execution=True,
)
def set_chat_focus(
    entity: str,
    id: str,
    meta: dict[str, Any] | None = None,
) -> str:
    return _client_only()


@tool(
    name="upload_document_inline",
    description=(
        "Open an inline upload dropzone in the chat so the user can drop a "
        "PDF or image without leaving the conversation. `accept` is the MIME "
        "list ('application/pdf', 'image/*', …); `purpose` is a short label "
        "shown to the user ('Importar tu CV', 'Foto de perfil'). Returns "
        "{uploaded: bool, file_url: string?, kind: 'pdf'|'image'|'other'}."
    ),
    external_execution=True,
)
def upload_document_inline(
    purpose: str,
    accept: str = "application/pdf",
    max_bytes: int = 10 * 1024 * 1024,
) -> str:
    return _client_only()


@tool(
    name="propose_esco_disambiguation",
    description=(
        "Ask the user to confirm which ESCO concept their entity refers to. "
        "Use this when the ESCO entity linker returns SUGGESTED — the personal "
        "skill / occupation could not be auto-linked with high enough confidence. "
        "Returns {chosen_uri: string?, dismissed: bool}; backend then attaches "
        "the LINKS_TO_ESCO edge if a URI was chosen."
    ),
    external_execution=True,
)
def propose_esco_disambiguation(
    quarantine_id: str,
    entity_kind: str,
    entity_label: str,
    candidates: list[dict[str, Any]],
) -> str:
    """`candidates` is a list of {uri, label, pref_label_es, pref_label_en, score}.
    The user picks one or dismisses; the resolver endpoint persists the choice.
    """
    return _client_only()


@tool(
    name="propose_edge_creation",
    description=(
        "Propose creating a typed edge between two existing entities in the "
        "user's graph (e.g. link a skill to a project, mark an ADR as part_of "
        "a project). Returns {accepted: bool}; backend creates the edge if "
        "accepted."
    ),
    external_execution=True,
)
def propose_edge_creation(
    source_entity_id: str,
    source_label: str,
    target_entity_id: str,
    target_label: str,
    edge_type: str,
    rationale: str | None = None,
) -> str:
    return _client_only()


@tool(
    name="propose_edge_deletion",
    description=(
        "Propose expiring (soft-deleting) an existing typed edge. Useful when "
        "the user says 'I'm not using X anymore' and the agent wants to mark "
        "the corresponding USES_TECH edge with valid_to=now()."
    ),
    external_execution=True,
)
def propose_edge_deletion(
    source_entity_id: str,
    target_entity_id: str,
    edge_type: str,
    rationale: str | None = None,
) -> str:
    return _client_only()


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
