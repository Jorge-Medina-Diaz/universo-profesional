/**
 * Shared chat-state.
 *
 * Two domains live here:
 *   1. ChatFocus — "which entity is the agent reasoning about right now"
 *      (set by the agent via the `set_chat_focus` tool, read by the rest of
 *      the app to highlight/pre-select).
 *   2. Widgets — an in-session stack of widgets the agent has summoned via
 *      `present_widget` so the user can browse structured data alongside
 *      the chat. Memory-only: refreshing the page clears them.
 */
import { create } from "zustand";
import type { AgentStatus } from "./agentState";

export type FocusEntity =
  | "job"
  | "document"
  | "note"
  | "experience"
  | "education"
  | "project"
  | "skill"
  | "certification"
  | "course"
  | "language"
  | "achievement"
  | "interest"
  // Sprint M-R graph entities — the agent can focus these too.
  | "artifact"
  | "architecture_decision"
  | "signal"
  | "episode";

interface ChatFocus {
  entity: FocusEntity | null;
  id: string | null;
  meta: Record<string, unknown> | null;
}

// Structured-entity widgets (skills_summary, certs_list, …) were retired
// in favour of the navigable graph at /universe. The kinds that remain
// are derived/analytical views that don't map onto a single graph node.
export type WidgetKind =
  | "job_match"
  | "document_preview"
  | "goals_progress"
  | "interview_qa"
  | "tech_radar"
  | "agent_patterns"
  | "signal_coverage"
  | "cloud_coverage"
  | "data_stack_topology"
  | "security_posture"
  | "architecture_patterns"
  | "portfolio_radar"
  | "learning_trajectory";

export interface ChatWidget {
  id: string;
  kind: WidgetKind;
  title: string;
  data: Record<string, unknown>;
  createdAt: number;
  pinned?: boolean;
}

const MAX_WIDGETS = 20;

interface ChatStateStore extends ChatFocus {
  setFocus: (focus: Partial<ChatFocus>) => void;
  clear: () => void;

  /** Active CopilotKit thread id (used for coherence upsert attribution). */
  activeSessionId: string | null;
  setActiveSessionId: (id: string | null) => void;

  /** Whether the floating chat panel is expanded (controlled externally + by user focus). */
  chatExpanded: boolean;
  setChatExpanded: (v: boolean) => void;

  /** One-shot message to inject into the chat thread (e.g. "Hablemos sobre X").
   *  Consumers must clear it after appending so it doesn't re-fire. */
  pendingInjection: { content: string } | null;
  setPendingInjection: (payload: { content: string } | null) => void;

  /** Live agent activity (mirrors the AG-UI shared state) so always-mounted
   *  chrome (FloatingChat's status chip) can show it WITHOUT importing
   *  CopilotKit. Written by CopilotSurface, null when idle. */
  agentActivity: { status: AgentStatus; label: string } | null;
  setAgentActivity: (a: { status: AgentStatus; label: string } | null) => void;

  /** One-shot page context handed off by `navigate_to` (and other writers,
   *  e.g. CommandPalette / kanban CV button) for the DESTINATION page to
   *  consume on mount. Replaces the old sessionStorage prefill hacks. */
  pendingPageContext: { route: string; context: Record<string, unknown>; ts: number } | null;
  setPendingPageContext: (
    payload: { route: string; context: Record<string, unknown> } | null,
  ) => void;
  /** Return-and-clear the pending context — only when `route` matches. */
  consumePageContext: (route: string) => Record<string, unknown> | null;

  widgets: ChatWidget[];
  addWidget: (
    w: Omit<ChatWidget, "id" | "createdAt"> & { id?: string },
  ) => string;
  removeWidget: (id: string) => void;
  togglePin: (id: string) => void;
  clearWidgets: () => void;
}

const initialFocus: ChatFocus = { entity: null, id: null, meta: null };

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `w_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

function widgetMatchesExisting(a: ChatWidget, b: ChatWidget): boolean {
  if (a.kind !== b.kind) return false;
  const aEntity = (a.data as { entity_id?: unknown }).entity_id;
  const bEntity = (b.data as { entity_id?: unknown }).entity_id;
  if (aEntity || bEntity) return aEntity === bEntity;
  return a.title === b.title;
}

export const useChatState = create<ChatStateStore>((set, get) => ({
  ...initialFocus,
  activeSessionId: null,
  setActiveSessionId: (id) => set({ activeSessionId: id }),
  chatExpanded: false,
  setChatExpanded: (v) => set({ chatExpanded: v }),
  pendingInjection: null,
  setPendingInjection: (payload) => set({ pendingInjection: payload }),
  agentActivity: null,
  setAgentActivity: (a) => set({ agentActivity: a }),
  pendingPageContext: null,
  setPendingPageContext: (payload) =>
    set({
      pendingPageContext: payload
        ? { route: payload.route, context: payload.context, ts: Date.now() }
        : null,
    }),
  consumePageContext: (route) => {
    const pending = get().pendingPageContext;
    if (!pending || pending.route !== route) return null;
    set({ pendingPageContext: null });
    return pending.context;
  },
  widgets: [],

  setFocus: (focus) =>
    set((prev) => ({
      entity: focus.entity ?? prev.entity,
      id: focus.id ?? prev.id,
      meta: focus.meta ?? prev.meta,
    })),

  clear: () => set(initialFocus),

  addWidget: (input) => {
    const id = input.id ?? newId();
    const next: ChatWidget = {
      id,
      kind: input.kind,
      title: input.title,
      data: input.data ?? {},
      createdAt: Date.now(),
      pinned: input.pinned ?? false,
    };
    set((prev) => {
      const dupIdx = prev.widgets.findIndex((w) => widgetMatchesExisting(w, next));
      let list: ChatWidget[];
      if (dupIdx >= 0) {
        list = [...prev.widgets];
        list[dupIdx] = { ...next, id: list[dupIdx].id, pinned: list[dupIdx].pinned };
      } else {
        list = [...prev.widgets, next];
      }
      if (list.length > MAX_WIDGETS) {
        const overflow = list.length - MAX_WIDGETS;
        const dropped: ChatWidget[] = [];
        const kept: ChatWidget[] = [];
        for (const w of list) {
          if (dropped.length < overflow && !w.pinned) dropped.push(w);
          else kept.push(w);
        }
        list = kept;
      }
      return { widgets: list };
    });
    return id;
  },

  removeWidget: (id) =>
    set((prev) => ({ widgets: prev.widgets.filter((w) => w.id !== id) })),

  togglePin: (id) =>
    set((prev) => ({
      widgets: prev.widgets.map((w) =>
        w.id === id ? { ...w, pinned: !w.pinned } : w,
      ),
    })),

  clearWidgets: () => set({ widgets: [] }),
}));
