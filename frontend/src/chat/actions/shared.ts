import { api } from "@/shared/api";
import { useChatState } from "../state";
import type { UpsertResponse } from "./types";

export async function resolveProposal(
  proposalId: string,
  action: "confirm" | "reject" | "modify",
  modifiedData?: Record<string, unknown>,
): Promise<UpsertResponse> {
  return api<UpsertResponse>(`/api/v1/agents/proposals/${proposalId}/resolve`, {
    method: "POST",
    body: JSON.stringify({ action, modified_data: modifiedData }),
  });
}

// Field whitelist per entity kind — the canonical payload each entity accepts.
// The batch-import card sends free-form LLM-extracted items, so a hallucinated
// field name (e.g. `obtained_date` instead of `issued_on`) would 500 the
// server-side `Entity.create(**payload)`. We normalise common aliases and drop
// unknown keys so one bad field never breaks an import.
export const IMPORT_FIELDS: Record<string, string[]> = {
  experience: ["organization", "role", "start_date", "end_date", "is_current", "description", "highlights", "competences"],
  education: ["institution", "degree", "field_of_study", "start_date", "end_date", "is_current", "description", "highlights"],
  project: ["name", "description", "role", "project_type", "tech_stack", "highlights", "impact", "url", "is_current"],
  skill: ["name", "category", "level", "years", "last_used_year"],
  certification: ["name", "issuer", "issued_on", "expires_on", "credential_id", "verification_url"],
  course: ["title", "platform", "started_on", "completed_on", "duration_hours", "certificate_url"],
  language: ["code", "name", "level", "certification"],
  achievement: ["title", "achieved_on", "description", "context", "evidence_url"],
  interest: ["name", "description"],
  artifact: ["type", "title", "url", "year", "description", "venue", "linked_project_id"],
};

// Common field-name variants the model emits → canonical name.
export const IMPORT_ALIASES: Record<string, string> = {
  obtained_date: "issued_on",
  issue_date: "issued_on",
  issued: "issued_on",
  granted_on: "issued_on",
  expiry_date: "expires_on",
  expiration_date: "expires_on",
  valid_until: "expires_on",
  completed_date: "completed_on",
  started_date: "started_on",
  achieved_date: "achieved_on",
  organisation: "organization",
  company: "organization",
};

// Common language names (ES/EN) → ISO 639-1, to backfill the required `code`
// when the model gives only the name.
export const LANG_CODE: Record<string, string> = {
  español: "es", castellano: "es", spanish: "es",
  inglés: "en", ingles: "en", english: "en",
  francés: "fr", frances: "fr", french: "fr",
  alemán: "de", aleman: "de", german: "de",
  italiano: "it", italian: "it",
  portugués: "pt", portugues: "pt", portuguese: "pt",
  neerlandés: "nl", neerlandes: "nl", holandés: "nl", holandes: "nl", dutch: "nl",
  catalán: "ca", catalan: "ca",
  gallego: "gl", euskera: "eu", vasco: "eu",
  chino: "zh", chinese: "zh", japonés: "ja", japones: "ja", japanese: "ja",
  ruso: "ru", russian: "ru", árabe: "ar", arabe: "ar", arabic: "ar",
};

export function normalizeImportItem(
  kind: string,
  raw: Record<string, unknown>,
): Record<string, unknown> {
  const allowed = IMPORT_FIELDS[kind];
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(raw)) {
    if (v === null || v === undefined || v === "") continue;
    const key = IMPORT_ALIASES[k] ?? k;
    if (!allowed || allowed.includes(key)) out[key] = v;
  }
  // Backfill required fields the model commonly omits.
  if (kind === "course" && !out.title && (raw.name || raw.title)) {
    out.title = (raw.name ?? raw.title) as string;
  }
  if (kind === "language" && !out.code && typeof out.name === "string") {
    const code = LANG_CODE[out.name.toLowerCase().trim()];
    if (code) out.code = code;
  }
  return out;
}

// Holder for the active chat thread id, updated by UniverseActions on
// every render. coherenceUpsert reads it so every entity persisted from a
// tool call is attributed to the current Episode.
export async function coherenceUpsert(
  entityKind: string,
  payload: Record<string, unknown>,
  opts?: { entityId?: string; opHint?: string; source?: string },
): Promise<UpsertResponse> {
  return api<UpsertResponse>("/api/v1/coherence/upsert", {
    method: "POST",
    body: JSON.stringify({
      entity_type: entityKind,
      payload,
      source: opts?.source ?? "agent_chat",
      chat_session_id: useChatState.getState().activeSessionId ?? undefined,
      op_hint: opts?.opHint,
      // When set, the engine updates THIS exact entity (manual inspector edit)
      // instead of name/semantic matching — same coherence path, no dup on rename.
      entity_id: opts?.entityId,
    }),
  });
}
