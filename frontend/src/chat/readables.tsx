/**
 * Curated `useCopilotReadable` payloads — what the agent sees each turn.
 * Token-budget conscious: we inject COMPACT snapshots, not full data.
 *
 * Sprint B: expanded from 2 to 8 readables so the agent can reason about
 * the whole product surface (jobs, documents, preferences, reminders,
 * integrations, tier) and not just universe entities. Each readable
 * caps its size to keep the prompt cheap.
 */
import { useCopilotReadable } from "@copilotkit/react-core";
import { useQuery } from "@tanstack/react-query";
import { chat, documents, jobs, universe, useAuthStore, auth } from "@/shared/api";
import { integrations, liveProfile } from "@/shared/api-extra";
import { useChatState } from "./state";
import { queryKeys } from "@/shared/queryKeys";

const FRESH_FOR_MS = 60_000;

export function UniverseReadable() {
  const isAuthed = !!useAuthStore((s) => s.accessToken);

  // --- Universe summary ---------------------------------------------------
  const summary = useQuery({
    queryKey: queryKeys.universe.summary,
    queryFn: () => universe.summary(),
    enabled: isAuthed,
    staleTime: FRESH_FOR_MS,
  });
  useCopilotReadable({
    description:
      "Compact summary of the user's professional universe (counts, headline, top skills, recent experiences, languages, integration status).",
    value: summary.data ?? { counts: {} },
  });

  // --- Conversation digest (long-term memory) ----------------------------
  // Everything older than the sliding window, compacted by the digest
  // workflow into open_questions / decisions / mentioned_entities/topics.
  // Lets the agent recall months of context without re-sending raw turns.
  const chatState = useQuery({
    queryKey: queryKeys.chat.state,
    queryFn: () => chat.state(),
    enabled: isAuthed,
    staleTime: FRESH_FOR_MS,
  });
  useCopilotReadable({
    description:
      "Digest of the conversation so far (older than the visible history): open questions, decisions made, and entities/topics discussed over time. Use it to stay coherent across long-running chats and avoid re-asking what's already settled.",
    value: chatState.data?.digest ?? null,
  });

  // --- Suggestions (top 15) ----------------------------------------------
  const suggestions = useQuery({
    queryKey: queryKeys.suggestions.all,
    queryFn: () => liveProfile.suggestions.list("pending"),
    enabled: isAuthed,
    staleTime: FRESH_FOR_MS,
  });
  useCopilotReadable({
    description:
      "Pending suggestions for the user's universe (skills to add, certs expiring, stale entries). Capped at the 15 most relevant to bound per-turn token cost.",
    // Hard cap: a power user can accumulate 100+ pending suggestions, and
    // this readable is injected on every turn. 15 is plenty for the agent
    // to act on without re-billing the whole backlog each message.
    value: (suggestions.data ?? []).slice(0, 15),
  });

  // --- Active jobs (top 10) ----------------------------------------------
  const jobsQ = useQuery({
    queryKey: queryKeys.jobs.all,
    queryFn: () => jobs.list(),
    enabled: isAuthed,
    staleTime: FRESH_FOR_MS,
  });
  useCopilotReadable({
    description:
      "User's job-tracker entries (active kanban). Top 10 most recent, compact shape: id, title, company, status, match_score, applied_at. Use to answer 'which jobs am I tracking?', '¿a cuál priorizo?', or to power `select_job_from_list`.",
    value: (jobsQ.data ?? []).slice(0, 10).map((j) => ({
      id: j.id,
      title: j.title,
      company: j.company_name,
      url: j.url,
      status: j.status,
      match_score: j.match_score,
      applied_at: j.applied_at,
      has_description: (j.description_raw ?? "").length > 30,
    })),
  });

  // --- Recent documents (top 6) ------------------------------------------
  const docsQ = useQuery({
    queryKey: queryKeys.documents.all,
    queryFn: () => documents.list(),
    enabled: isAuthed,
    staleTime: FRESH_FOR_MS,
  });
  useCopilotReadable({
    description:
      "Recently generated documents (CVs + cover letters). Top 6, with kind/template/language/created_at flags. Use for `select_document_from_list` or when the user asks about their CV variants.",
    value: (docsQ.data ?? []).slice(0, 6).map((d) => ({
      id: d.id,
      kind: d.kind,
      template: d.template,
      language: d.language,
      tone: d.tone,
      created_at: d.created_at,
      has_pdf: d.has_pdf,
      has_docx: d.has_docx,
    })),
  });

  // --- Career preferences -------------------------------------------------
  const prefsQ = useQuery({
    queryKey: queryKeys.universe.preferences,
    queryFn: () => universe.preferences.get(),
    enabled: isAuthed,
    staleTime: FRESH_FOR_MS,
  });
  useCopilotReadable({
    description:
      "User's career preferences (target status, salary range, contract types, remote preference, working areas, perks, preferred/discarded competences and roles, motivations). Null if never set. Use to gate job recommendations and to suggest `propose_preferences_update` when the user mentions changes.",
    value: prefsQ.data ?? null,
  });

  // --- Pending reminders (top 5) -----------------------------------------
  const remindersQ = useQuery({
    queryKey: queryKeys.reminders.pending,
    queryFn: () => universe.reminders.list(),
    enabled: isAuthed,
    staleTime: FRESH_FOR_MS,
  });
  useCopilotReadable({
    description:
      "User's pending reminders (certs expiring, courses gone stale, entries to review). Top 5, with due_at. Surface them proactively when relevant ('tu cert X vence en 12 días, ¿la renuevas?').",
    value: (remindersQ.data ?? []).slice(0, 5).map((r) => ({
      id: r.id,
      kind: r.kind,
      title: r.title,
      body: r.body,
      due_at: r.due_at,
    })),
  });

  // --- Integrations status ------------------------------------------------
  const intsQ = useQuery({
    queryKey: queryKeys.integrations.list,
    queryFn: () => integrations.list(),
    enabled: isAuthed,
    staleTime: FRESH_FOR_MS,
  });
  useCopilotReadable({
    description:
      "Connected external accounts (GitHub, LinkedIn, etc.) with last sync timestamp. Use to know whether to suggest a re-sync or which onboarding path is still pending.",
    value: (intsQ.data?.connections ?? []).map((c) => ({
      provider: c.provider,
      username: c.username,
      connected_at: c.connected_at,
      last_synced_at: c.last_synced_at,
      sync_status: c.sync_status,
    })),
  });

  // --- Active chat focus (Sprint D — closes the loop UI ↔ agent) ---------
  const focus = useChatState();
  useCopilotReadable({
    description:
      "Active chat focus — which entity the agent is currently reasoning about (set by `set_chat_focus`). If set, prefer to keep the conversation tight around this entity unless the user explicitly pivots away. `entity` is one of: job, document, skill, experience, note. `id` is the entity uuid. `meta` carries any free-form context the agent stored.",
    value:
      focus.entity && focus.id
        ? { entity: focus.entity, id: focus.id, meta: focus.meta }
        : null,
  });

  // --- Tier ---------------------------------------------------------------
  const meQ = useQuery({
    queryKey: queryKeys.me.all,
    queryFn: () => auth.me(),
    enabled: isAuthed,
    staleTime: 5 * FRESH_FOR_MS,
  });
  useCopilotReadable({
    description:
      "User's subscription tier ('free' or 'pro'). Gate PRO-only feature suggestions (Bright Data LinkedIn sync, advanced analytics) accordingly.",
    value: meQ.data ? { tier: meQ.data.tier, email: meQ.data.email } : null,
  });

  return null;
}
