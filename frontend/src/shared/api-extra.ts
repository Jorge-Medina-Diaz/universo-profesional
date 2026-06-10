/**
 * Sprint-2 API additions: integrations, suggestions, reminders, activity, evidence, photo.
 *
 * Lives alongside `api.ts` to keep the original surface stable for the MVP pages.
 */
import { api, useAuthStore } from "./api";

// --- Integrations ---

export interface Connection {
  provider: string;
  username: string | null;
  scopes: string[];
  connected_at: string;
  last_synced_at: string | null;
  sync_status: string | null;
  sync_error: string | null;
  metadata: { name?: string; avatar_url?: string; html_url?: string };
}

export const integrations = {
  list: () => api<{ connections: Connection[] }>("/api/v1/integrations"),
  syncRuns: (limit = 10) =>
    api<{ runs: Array<Record<string, unknown>> }>(
      `/api/v1/integrations/sync-runs?limit=${limit}`,
    ),
  cancelSyncRun: (id: string) =>
    api<{ ok: boolean; error?: string }>(
      `/api/v1/integrations/sync-runs/${id}/cancel`,
      { method: "POST" },
    ),
  github: {
    authorizeUrl: () =>
      api<{ authorize_url: string }>("/api/v1/integrations/github/authorize"),
    sync: () =>
      api<Record<string, unknown>>("/api/v1/integrations/github/sync", { method: "POST" }),
    /** Fire-and-forget: enqueues the sync on the Arq worker. Returns
     *  immediately with `{queued, job_id, mode}`. UI shows progress through
     *  the existing `SyncTaskTray` polling — no need to await this. */
    syncAsync: () =>
      api<{ queued: boolean; job_id: string | null; mode: string }>(
        "/api/v1/integrations/github/sync-async",
        { method: "POST" },
      ),
    disconnect: () =>
      api("/api/v1/integrations/github", { method: "DELETE" }),
  },
  linkedin: {
    // --- OIDC sign-in (also usable to link an existing user) ---
    // Backend returns { configured: false, authorize_url: "" } when LinkedIn
    // credentials aren't set — callers must check `configured` before redirecting.
    oidcAuthorize: (linkUserId?: string) =>
      api<{ authorize_url: string; state: string; configured: boolean }>(
        `/api/v1/auth/linkedin/authorize${linkUserId ? `?link=${linkUserId}` : ""}`,
        { authRequired: false },
      ),
    // --- Status probe: tells UI which LinkedIn paths use fixtures vs real APIs ---
    status: () =>
      api<{
        oidc: { configured: boolean };
        dma: { configured: boolean; enabled: boolean; uses_fixture: boolean };
        brightdata: { configured: boolean; uses_fixture: boolean };
        zip: { configured: boolean; uses_fixture: boolean };
      }>("/api/v1/integrations/linkedin/status"),
    // --- ZIP fallback (free, offline-friendly) ---
    parseZip: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      const resp = await fetch("/api/v1/integrations/linkedin/zip/parse", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ""}`,
        },
        body: fd,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(
          (err as { detail?: string }).detail ?? `HTTP ${resp.status}`,
        );
      }
      return resp.json();
    },
    // `selection` maps kind → indices into parsed[kind]; only listed items
    // commit, and a kind ABSENT from the map commits nothing — callers doing
    // granular review must include EVERY kind key (empty array = skip kind).
    // Omitting `selection` keeps the legacy commit-everything behaviour.
    commitZip: (session_id: string, selection?: Record<string, number[]>) =>
      api<Record<string, unknown>>("/api/v1/integrations/linkedin/zip/commit", {
        method: "POST",
        body: JSON.stringify(selection ? { session_id, selection } : { session_id }),
      }),
    // Legacy alias for older callers
    commit: (session_id: string) =>
      api<Record<string, unknown>>("/api/v1/integrations/linkedin/zip/commit", {
        method: "POST",
        body: JSON.stringify({ session_id }),
      }),
    // --- DMA 3rd-party API (EEA users, free, requires approval) ---
    dma: {
      authorizeUrl: () =>
        api<{ authorize_url: string; dma_enabled: string }>(
          "/api/v1/integrations/linkedin/dma/authorize",
        ),
      sync: () =>
        api<{ session_id: string; parsed: Record<string, unknown> }>(
          "/api/v1/integrations/linkedin/dma/sync",
          { method: "POST" },
        ),
      commit: (session_id: string, selection?: Record<string, number[]>) =>
        api<Record<string, unknown>>("/api/v1/integrations/linkedin/dma/commit", {
          method: "POST",
          body: JSON.stringify({ session_id, selection }),
        }),
      disconnect: () =>
        api("/api/v1/integrations/linkedin/dma", { method: "DELETE" }),
    },
    // --- Bright Data 3rd-party (PRO tier, paid per lookup, works globally) ---
    brightdata: {
      sync: (body: { linkedin_url?: string; fresh?: boolean }) =>
        api<{ session_id: string; parsed: Record<string, unknown> }>(
          "/api/v1/integrations/linkedin/brightdata/sync",
          { method: "POST", body: JSON.stringify(body) },
        ),
      commit: (session_id: string, selection?: Record<string, number[]>) =>
        api<Record<string, unknown>>(
          "/api/v1/integrations/linkedin/brightdata/commit",
          {
            method: "POST",
            body: JSON.stringify({ session_id, selection }),
          },
        ),
    },
  },
  pdf: {
    parse: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      const resp = await fetch("/api/v1/integrations/pdf/parse", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ""}`,
        },
        body: fd,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(
          (err as { detail?: string }).detail ?? `HTTP ${resp.status}`,
        );
      }
      return resp.json();
    },
    commit: (session_id: string, selection?: Record<string, number[]>) =>
      api<Record<string, unknown>>("/api/v1/integrations/pdf/commit", {
        method: "POST",
        body: JSON.stringify({ session_id, selection }),
      }),
  },
};

// --- Suggestions / Reminders / Activity ---

export interface Suggestion {
  id: string;
  kind: string;
  title: string;
  body: string | null;
  payload: Record<string, unknown> | null;
  priority: number;
  status: string;
}

export interface Reminder {
  id: string;
  kind: string;
  subject_type: string | null;
  subject_id: string | null;
  title: string;
  body: string | null;
  due_at: string;
  payload: Record<string, unknown> | null;
  created_at: string;
}

export const liveProfile = {
  suggestions: {
    regenerate: () =>
      api<Suggestion[]>("/api/v1/universe/suggestions/regenerate", { method: "POST" }),
    list: (status = "pending") => api<Suggestion[]>(`/api/v1/universe/suggestions?status=${status}`),
    act: (id: string, action: "accept" | "reject") =>
      api(`/api/v1/universe/suggestions/${id}/act`, {
        method: "POST",
        body: JSON.stringify({ action }),
      }),
  },
  reminders: {
    list: (due_within_days?: number) =>
      api<Reminder[]>(
        `/api/v1/universe/reminders${due_within_days ? `?due_within_days=${due_within_days}` : ""}`,
      ),
    scan: () =>
      api<{ created: number }>("/api/v1/universe/reminders/scan", { method: "POST" }),
    dismiss: (id: string) =>
      api(`/api/v1/universe/reminders/${id}/dismiss`, { method: "POST" }),
  },
  activity: async (limit = 50): Promise<Array<Record<string, unknown>>> => {
    // The endpoint returns a {items, next_cursor} envelope now; unwrap it so
    // this helper keeps its array contract (the canonical client is
    // universe.activity() in api.ts).
    const page = await api<{
      items: Array<Record<string, unknown>>;
      next_cursor: string | null;
    }>(`/api/v1/universe/activity?limit=${limit}`);
    return page.items;
  },
  markReviewed: (entity_type: string, entity_id: string) =>
    api("/api/v1/universe/mark-reviewed", {
      method: "POST",
      body: JSON.stringify({ entity_type, entity_id }),
    }),
  linkEvidence: (body: {
    skill_id: string;
    evidence_entity_type: string;
    evidence_entity_id: string;
    weight?: number;
    notes?: string;
  }) =>
    api("/api/v1/universe/evidence", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listEvidence: (skill_id?: string) =>
    api<Array<Record<string, unknown>>>(
      `/api/v1/universe/evidence${skill_id ? `?skill_id=${skill_id}` : ""}`,
    ),
};

// --- Photo ---

// --- LLM Usage ---

export const llmUsage = {
  summary: (year?: number, month?: number) => {
    const qs = new URLSearchParams();
    if (year) qs.set("year", String(year));
    if (month) qs.set("month", String(month));
    const qstr = qs.toString();
    return api<{
      period: { year: number; month: number };
      summary: {
        total_cost_eur: number;
        total_tokens: number;
        input_tokens: number;
        output_tokens: number;
        by_model: Array<{
          model: string;
          cost_eur: number;
          tokens: number;
          runs: number;
        }>;
        by_agent: Array<{
          agent: string;
          cost_eur: number;
          tokens: number;
          runs: number;
        }>;
      };
      daily: Array<{
        day: string;
        input_tokens: number;
        output_tokens: number;
        total_tokens: number;
        cost_eur: number;
      }>;
      free_tier_tokens: number;
    }>(`/api/v1/llm/usage${qstr ? `?${qstr}` : ""}`);
  },
  sessions: (limit = 50) =>
    api<{
      sessions: Array<{
        session_id: string;
        cost_eur: number;
        tokens: number;
        runs: number;
        last_used: string | null;
      }>;
    }>(`/api/v1/llm/usage/sessions?limit=${limit}`),
};

export const photo = {
  upload: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const resp = await fetch("/api/v1/users/me/photo", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ""}`,
      },
      body: fd,
    });
    if (!resp.ok) throw new Error(`upload failed: ${resp.status}`);
    return resp.json();
  },
  url: () => "/api/v1/users/me/photo",
  /**
   * Load the avatar as an authenticated blob → object URL. A plain
   * `<img src="/api/v1/users/me/photo">` can't send the Bearer header, so it
   * always 401s and spams the console; this fetches with auth and returns a
   * usable object URL, or null when there's no photo (so callers show a
   * placeholder instead of a broken request).
   */
  load: async (): Promise<string | null> => {
    const token = useAuthStore.getState().accessToken;
    if (!token) return null;
    try {
      const resp = await fetch("/api/v1/users/me/photo", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) return null;
      const blob = await resp.blob();
      if (blob.size === 0) return null;
      return URL.createObjectURL(blob);
    } catch {
      return null;
    }
  },
  remove: () => api("/api/v1/users/me/photo", { method: "DELETE" }),
};
