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
  github: {
    authorizeUrl: () =>
      api<{ authorize_url: string }>("/api/v1/integrations/github/authorize"),
    sync: () =>
      api<Record<string, unknown>>("/api/v1/integrations/github/sync", { method: "POST" }),
    disconnect: () =>
      api("/api/v1/integrations/github", { method: "DELETE" }),
  },
  linkedin: {
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
      return resp.json();
    },
    commit: (session_id: string) =>
      api<Record<string, unknown>>("/api/v1/integrations/linkedin/zip/commit", {
        method: "POST",
        body: JSON.stringify({ session_id }),
      }),
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
  activity: (limit = 50) =>
    api<Array<Record<string, unknown>>>(`/api/v1/universe/activity?limit=${limit}`),
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
  remove: () => api("/api/v1/users/me/photo", { method: "DELETE" }),
};
