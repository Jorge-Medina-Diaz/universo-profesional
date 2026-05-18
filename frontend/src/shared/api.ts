/**
 * Minimal API client: typed fetch + token management via Zustand.
 */
import { create } from "zustand";

export interface AuthTokens {
  accessToken: string | null;
  refreshToken: string | null;
  userId: string | null;
  email: string | null;
}

interface AuthState extends AuthTokens {
  setTokens: (t: AuthTokens) => void;
  clear: () => void;
}

const STORAGE_KEY = "cvs-saas-auth";

function loadFromStorage(): AuthTokens {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyTokens();
    return JSON.parse(raw) as AuthTokens;
  } catch {
    return emptyTokens();
  }
}

function emptyTokens(): AuthTokens {
  return { accessToken: null, refreshToken: null, userId: null, email: null };
}

export const useAuthStore = create<AuthState>((set) => ({
  ...loadFromStorage(),
  setTokens: (t) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
    set(t);
  },
  clear: () => {
    localStorage.removeItem(STORAGE_KEY);
    set(emptyTokens());
  },
}));

export class ApiError extends Error {
  constructor(public status: number, public payload: unknown, message?: string) {
    super(message ?? `API error ${status}`);
  }
}

async function authHeader(): Promise<Record<string, string>> {
  const { accessToken } = useAuthStore.getState();
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit & { authRequired?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init.body ? { "Content-Type": "application/json" } : {}),
    ...(init.authRequired === false ? {} : await authHeader()),
    ...((init.headers as Record<string, string>) ?? {}),
  };
  const resp = await fetch(path, { ...init, headers });
  if (resp.status === 204) return undefined as T;
  const text = await resp.text();
  const parsed = text ? safeJson(text) : undefined;
  if (!resp.ok) {
    if (resp.status === 401) {
      const refreshed = await tryRefresh();
      if (refreshed) return api<T>(path, init);
      useAuthStore.getState().clear();
    }
    throw new ApiError(resp.status, parsed, typeof parsed === "object" && parsed && "title" in parsed ? String((parsed as { title: unknown }).title) : undefined);
  }
  return parsed as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function tryRefresh(): Promise<boolean> {
  const { refreshToken } = useAuthStore.getState();
  if (!refreshToken) return false;
  try {
    const resp = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!resp.ok) return false;
    const t = await resp.json();
    useAuthStore.getState().setTokens({
      accessToken: t.access_token,
      refreshToken: t.refresh_token,
      userId: t.user_id,
      email: t.email,
    });
    return true;
  } catch {
    return false;
  }
}

// --- Typed helpers ---

export const auth = {
  register: (b: { email: string; password: string; display_name?: string; locale?: string }) =>
    api<{ user_id: string; email: string; verification_link?: string }>(
      "/api/v1/auth/register",
      { method: "POST", body: JSON.stringify(b), authRequired: false },
    ),
  verify: (token: string) =>
    api("/api/v1/auth/verify", { method: "POST", body: JSON.stringify({ token }), authRequired: false }),
  login: (b: { email: string; password: string }) =>
    api<{ access_token: string; refresh_token: string; user_id: string; email: string }>(
      "/api/v1/auth/login",
      { method: "POST", body: JSON.stringify(b), authRequired: false },
    ),
  me: () => api<MeResponse>("/api/v1/users/me"),
  deleteMe: () => api("/api/v1/users/me", { method: "DELETE" }),
};

export interface MeResponse {
  user_id: string;
  email: string;
  display_name: string | null;
  locale: string;
  email_verified: boolean;
  mfa_enabled: boolean;
  created_at: string;
}

export const universe = {
  summary: () => api<UniverseSummary>("/api/v1/universe/summary"),
  list: (kind: string) => api<Record<string, unknown>[]>(`/api/v1/universe/${kind}`),
  add: (kind: string, body: Record<string, unknown>) =>
    api(`/api/v1/universe/${kind}`, { method: "POST", body: JSON.stringify(body) }),
  patch: (kind: string, id: string, body: Record<string, unknown>) =>
    api(`/api/v1/universe/${kind}/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  remove: (kind: string, id: string) =>
    api(`/api/v1/universe/${kind}/${id}`, { method: "DELETE" }),
  patchHeader: (body: Record<string, unknown>) =>
    api("/api/v1/universe/header", { method: "PATCH", body: JSON.stringify(body) }),
  importLinkedIn: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetch("/api/v1/import/linkedin", {
      method: "POST",
      headers: { Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ""}` },
      body: fd,
    }).then((r) => r.json());
  },
};

export interface UniverseSummary {
  headline: string | null;
  summary: string | null;
  photo_url: string | null;
  current_status: string | null;
  counts: { educations: number; experiences: number; projects: number; skills: number; languages: number };
  top_skills: Record<string, unknown>[];
  recent_experiences: Record<string, unknown>[];
  languages: Record<string, unknown>[];
  preferences: Record<string, unknown> | null;
}

export const documents = {
  list: () => api<DocumentSummary[]>("/api/v1/documents"),
  get: (id: string) => api<DocumentDetail>(`/api/v1/documents/${id}`),
  generate: (b: { job_description?: string; job_url?: string; template?: string; language?: string; tone?: string }) =>
    api<GenerateCvResponse>("/api/v1/documents/generate-cv", { method: "POST", body: JSON.stringify(b) }),
  share: (id: string) => api<{ share_token: string; share_url: string }>(`/api/v1/documents/${id}/share`, { method: "POST" }),
};

export interface DocumentSummary {
  id: string;
  kind: string;
  template: string;
  language: string;
  tone: string | null;
  length: string | null;
  created_at: string;
  has_pdf: boolean;
  has_docx: boolean;
  share_token: string | null;
}
export interface DocumentDetail extends DocumentSummary {
  content_json: Record<string, unknown>;
}
export interface GenerateCvResponse {
  document_id: string;
  pdf_url: string | null;
  docx_url: string | null;
  json_resume: Record<string, unknown>;
}

export const billing = {
  plans: () => api<{ plans: Plan[] }>("/api/v1/billing/plans", { authRequired: false }),
  subscription: () => api<SubscriptionDto>("/api/v1/billing/subscription"),
  upgrade: (plan: "premium" | "pro") =>
    api<SubscriptionDto>("/api/v1/billing/webhook/test", {
      method: "POST",
      body: JSON.stringify({ event: "checkout.completed", user_id: useAuthStore.getState().userId, plan }),
      authRequired: false,
    }),
  cancel: () => api<SubscriptionDto>("/api/v1/billing/cancel", { method: "POST" }),
};

export interface Plan {
  id: string;
  name: string;
  price_eur_month: number;
  price_eur_year?: number;
  limits: { monthly_cv: number; monthly_cover_letters: number; mcp_access: boolean; mcp_daily_calls: number };
}
export interface SubscriptionDto {
  plan: "free" | "premium" | "pro";
  status: string;
  trial_ends_at: string | null;
  current_period_end: string | null;
  limits?: Plan["limits"];
}
