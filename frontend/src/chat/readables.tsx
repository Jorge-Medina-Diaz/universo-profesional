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
import { graphApi } from "@/graph/api";
import { useGraphLensState } from "@/graph/lensState";
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
  // agno's native session summary ({summary, topics}), maintained by the
  // framework on every run — replaced the custom sliding-window digest.
  const chatState = useQuery({
    queryKey: queryKeys.chat.state,
    queryFn: () => chat.state(),
    enabled: isAuthed,
    staleTime: FRESH_FOR_MS,
  });
  useCopilotReadable({
    description:
      "Summary of the conversation so far (older than the visible history) plus its topics. Use it to stay coherent across long-running chats and avoid re-asking what's already settled.",
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

  // --- Graph view (agent SEES + can pilot the constellation) -------------
  // Closes the loop: the agent reads the current lens + filters + a sample of
  // visible nodes, then drives the view with control_graph / animate_graph
  // against REAL ids/labels instead of hallucinating.
  const graphSnap = useQuery({
    queryKey: queryKeys.graph.snapshot,
    queryFn: () => graphApi.snapshot(false),
    enabled: isAuthed,
    staleTime: FRESH_FOR_MS,
  });
  const lens = useGraphLensState();
  // Token trim: the node sample is the heavy part of this readable and it used
  // to ship on EVERY turn (40 nodes ≈ ~600 tok) even when the user is just
  // adding a skill. Only include the sample when a graph context is actually in
  // play (a focus/search/local-graph view) or the graph is small enough to be
  // free; otherwise ship just the tiny lens-state + counts. The agent still
  // sees node_count (so it knows the graph isn't empty) and can call
  // `universe_retrieve` for specific ids when it needs them.
  const nodeCount = graphSnap.data?.node_count ?? 0;
  const graphActive = !!(lens.focusEntityId || lens.search || lens.localGraph);
  const includeSample = graphActive || nodeCount <= 15;
  const nodeSample = includeSample
    ? (graphSnap.data?.nodes ?? []).slice(0, 15).map((n) => ({
        id: n.key,
        label: n.attributes.label,
        kind: n.attributes.kind,
        area: n.attributes.area ?? null,
      }))
    : [];
  useCopilotReadable({
    description:
      "The user's CURRENT /universe graph view: lens mode, focused entity, active filters (kinds / hidden areas / colour-by / search / local-graph depth) and counts. A sample of visible nodes (id/label/kind/area, capped at 15) is included ONLY when a graph view is active (focus/search/local-graph) or the graph is small — on other turns `nodes` is empty to save tokens; use `universe_retrieve` to look up specific ids. Ground every graph command on this: `control_graph` to filter/hide-areas/switch-lens/focus and `animate_graph` to fly the camera or pulse node sets, using real entity ids/labels.",
    value: {
      mode: lens.mode,
      focus_entity_id: lens.focusEntityId,
      color_by: lens.colorBy,
      local_graph: lens.localGraph,
      depth: lens.depth,
      search: lens.search || null,
      filter_kinds: Array.from(lens.activeKinds),
      hidden_areas: Array.from(lens.hiddenAreas),
      node_count: nodeCount,
      edge_count: graphSnap.data?.edge_count ?? 0,
      nodes: nodeSample,
      nodes_sampled: includeSample,
    },
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
