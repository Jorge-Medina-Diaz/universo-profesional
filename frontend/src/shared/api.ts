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

/**
 * Extract a human-readable message from any shape the backend returns:
 *   - FastAPI HTTPException → { detail: "..." } | { detail: { error, message, ... } }
 *   - DomainError problem → { title, detail }
 *   - String → use as-is
 */
function extractErrorMessage(status: number, payload: unknown): string {
  if (typeof payload === "string" && payload) return payload;
  if (payload && typeof payload === "object") {
    const p = payload as Record<string, unknown>;
    // FastAPI: detail
    if (typeof p.detail === "string") return p.detail;
    if (p.detail && typeof p.detail === "object") {
      const d = p.detail as Record<string, unknown>;
      if (typeof d.message === "string") return d.message;
      if (typeof d.error === "string") return d.error;
      return JSON.stringify(d);
    }
    // RFC 7807 / DomainError
    if (typeof p.title === "string") {
      return p.detail && typeof p.detail === "string"
        ? `${p.title}: ${p.detail}`
        : p.title;
    }
    if (typeof p.message === "string") return p.message;
  }
  return `HTTP ${status}`;
}

async function authHeader(): Promise<Record<string, string>> {
  const { accessToken } = useAuthStore.getState();
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit & { authRequired?: boolean; _retried?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init.body ? { "Content-Type": "application/json" } : {}),
    ...(init.authRequired === false ? {} : await authHeader()),
    ...((init.headers as Record<string, string>) ?? {}),
  };
  let resp: Response;
  try {
    resp = await fetch(path, { ...init, headers });
  } catch (networkError) {
    throw new ApiError(0, null, `Sin conexión al backend: ${(networkError as Error).message}`);
  }
  if (resp.status === 204) {
    return undefined as T;
  }
  const text = await resp.text();
  const parsed = text ? safeJson(text) : undefined;
  if (!resp.ok) {
    // Retry once after a token refresh. The `_retried` guard prevents an
    // infinite loop if the refreshed token is also rejected.
    if (resp.status === 401 && init.authRequired !== false && !init._retried) {
      const refreshed = await tryRefresh();
      if (refreshed) return api<T>(path, { ...init, _retried: true });
      useAuthStore.getState().clear();
    }
    throw new ApiError(resp.status, parsed, extractErrorMessage(resp.status, parsed));
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

// Single-flight refresh: concurrent 401s (page mount fires many queries at
// once) must NOT each POST /auth/refresh. The backend ROTATES the refresh
// token, so the first call invalidates it and every other concurrent call
// would fail → clear() → the user gets logged out mid-session. Coalescing
// into one shared in-flight promise means the token is consumed exactly once
// and all waiters retry with the same rotated access token.
let _refreshInFlight: Promise<boolean> | null = null;

function tryRefresh(): Promise<boolean> {
  if (_refreshInFlight) return _refreshInFlight;
  _refreshInFlight = doRefresh().finally(() => {
    _refreshInFlight = null;
  });
  return _refreshInFlight;
}

async function doRefresh(): Promise<boolean> {
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

// --- Proactive token refresh -------------------------------------------------
// The reactive 401→refresh path above recovers an *expired* token, but only
// after a request has already failed — a brief flash where a query (or the
// CopilotKit chat, which reads the token per request) errors before recovering.
// To keep long/idle sessions seamless we also refresh ~90s BEFORE the access
// token's `exp`, and immediately when a backgrounded tab becomes visible near
// or past expiry (timers are throttled while hidden). All paths funnel through
// the single-flight `tryRefresh`, so the rotating refresh token is consumed once.

const REFRESH_SKEW_MS = 90_000;
let _refreshTimer: ReturnType<typeof setTimeout> | null = null;
let _autoRefreshStarted = false;

/** Read the `exp` (ms epoch) from a JWT without verifying it. Null if unparseable. */
function decodeJwtExpMs(token: string): number | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const json = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return typeof json.exp === "number" ? json.exp * 1000 : null;
  } catch {
    return null;
  }
}

function scheduleProactiveRefresh(): void {
  if (_refreshTimer) {
    clearTimeout(_refreshTimer);
    _refreshTimer = null;
  }
  const { accessToken, refreshToken } = useAuthStore.getState();
  if (!accessToken || !refreshToken) return;
  const expMs = decodeJwtExpMs(accessToken);
  if (expMs == null) return;
  const delay = Math.max(0, expMs - Date.now() - REFRESH_SKEW_MS);
  _refreshTimer = setTimeout(() => {
    void tryRefresh();
  }, delay);
}

function onVisibilityChange(): void {
  if (document.visibilityState !== "visible") return;
  const { accessToken, refreshToken } = useAuthStore.getState();
  if (!accessToken || !refreshToken) return;
  const expMs = decodeJwtExpMs(accessToken);
  if (expMs == null) return;
  if (expMs - Date.now() < REFRESH_SKEW_MS) void tryRefresh();
  else scheduleProactiveRefresh();
}

/**
 * Start proactive token refresh. Idempotent; call once at app startup. Reschedules
 * whenever the access token changes (login, silent refresh, logout) and refreshes
 * on tab re-focus when the token is near/past expiry. A proactive failure is left
 * to the reactive 401 path (which clears the session) rather than logging out from
 * a background timer.
 */
export function startTokenAutoRefresh(): void {
  if (_autoRefreshStarted) return;
  _autoRefreshStarted = true;
  useAuthStore.subscribe((state, prev) => {
    if (state.accessToken !== prev.accessToken) scheduleProactiveRefresh();
  });
  if (typeof document !== "undefined") {
    document.addEventListener("visibilitychange", onVisibilityChange);
  }
  scheduleProactiveRefresh();
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
    api<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(b),
      authRequired: false,
    }),
  mfaLogin: (b: { mfa_token: string; code: string }) =>
    api<TokenResponse>("/api/v1/auth/mfa", {
      method: "POST",
      body: JSON.stringify(b),
      authRequired: false,
    }),
  requestPasswordReset: (email: string) =>
    api("/api/v1/auth/password-reset", {
      method: "POST",
      body: JSON.stringify({ email }),
      authRequired: false,
    }),
  confirmPasswordReset: (token: string, new_password: string) =>
    api("/api/v1/auth/password-reset/confirm", {
      method: "POST",
      body: JSON.stringify({ token, new_password }),
      authRequired: false,
    }),
  me: () => api<MeResponse>("/api/v1/users/me"),
  deleteMe: () => api("/api/v1/users/me", { method: "DELETE" }),
  mfa: {
    setup: () =>
      api<{ secret: string; otpauth_uri: string }>("/api/v1/users/me/mfa/setup", {
        method: "POST",
      }),
    confirm: (code: string) =>
      api<{ mfa_enabled: boolean }>("/api/v1/users/me/mfa/confirm", {
        method: "POST",
        body: JSON.stringify({ code }),
      }),
    disable: (code: string) =>
      api<{ mfa_enabled: boolean }>("/api/v1/users/me/mfa/disable", {
        method: "POST",
        body: JSON.stringify({ code }),
      }),
  },
};

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  user_id: string;
  email: string;
  mfa_required?: boolean;
  mfa_token?: string | null;
}

export interface MeResponse {
  user_id: string;
  email: string;
  display_name: string | null;
  locale: string;
  email_verified: boolean;
  mfa_enabled: boolean;
  created_at: string;
  tier: Tier;
  tier_updated_at: string | null;
}

export type Tier = "free" | "pro" | "premium";

/** Canonical paid-entitlement check — premium counts as paid (mirrors the
 *  backend is_paying gate). Use this for feature gating, NOT `tier === "pro"`. */
export function isPayingTier(tier: Tier | string | null | undefined): boolean {
  return tier === "pro" || tier === "premium";
}

export interface NotificationPrefs {
  email_reminders: boolean;
}

export const account = {
  setTier: (tier: "free" | "pro") =>
    api<MeResponse>("/api/v1/users/me/tier", {
      method: "POST",
      body: JSON.stringify({ tier }),
    }),
  getNotificationPrefs: () =>
    api<NotificationPrefs>("/api/v1/users/me/notifications"),
  setNotificationPrefs: (prefs: NotificationPrefs) =>
    api<NotificationPrefs>("/api/v1/users/me/notifications", {
      method: "PATCH",
      body: JSON.stringify(prefs),
    }),
  llmKey: {
    get: () => api<LlmKeyStatus>("/api/v1/agents/llm-key"),
    set: (provider: string, api_key: string) =>
      api<LlmKeyStatus>("/api/v1/agents/llm-key", {
        method: "PUT",
        body: JSON.stringify({ provider, api_key }),
      }),
    clear: () => api<LlmKeyStatus>("/api/v1/agents/llm-key", { method: "DELETE" }),
  },
};

export interface LlmKeyStatus {
  configured: boolean;
  provider: string | null;
}

export interface ChatSession {
  session_id: string;
  title: string | null;
  pinned: boolean;
  archived: boolean;
  created_at: string;
  updated_at: string;
}

export const chatSessions = {
  list: () => api<ChatSession[]>("/api/v1/chat/sessions"),
  create: (title?: string) =>
    api<ChatSession>("/api/v1/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ title: title ?? null }),
    }),
  get: (id: string) => api<ChatSession>(`/api/v1/chat/sessions/${id}`),
  update: (id: string, body: Partial<Pick<ChatSession, "title" | "pinned" | "archived">>) =>
    api<ChatSession>(`/api/v1/chat/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  remove: (id: string) =>
    api<void>(`/api/v1/chat/sessions/${id}`, { method: "DELETE" }),
};

export interface ChatStateResponse {
  session_id: string;
  digest: Record<string, unknown> | null;
  message_count: number;
}

export const chat = {
  // Long-term conversation memory: the digest of everything older than the
  // sliding window, computed by the session-digest workflow. Injected into
  // the agent context as a readable so long chats stay coherent cheaply.
  state: () => api<ChatStateResponse>("/api/v1/chat/state"),
};

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
  // Parse a CV PDF into reviewable candidates (server extracts text + LLM
  // structures it). Does NOT commit — the caller reviews and posts the
  // accepted entries via universe.add(). Surfaces server/HTTP errors instead
  // of swallowing them.
  importPdf: async (file: File): Promise<CvParseResult> => {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch("/api/v1/import/pdf", {
      method: "POST",
      headers: { Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ""}` },
      body: fd,
    });
    if (!r.ok) {
      throw new Error(`No se pudo analizar el PDF (HTTP ${r.status})`);
    }
    return r.json();
  },
  reminders: {
    list: (dueWithinDays?: number) => {
      const qs = dueWithinDays != null ? `?due_within_days=${dueWithinDays}` : "";
      return api<ReminderRow[]>(`/api/v1/universe/reminders${qs}`);
    },
    dismiss: (id: string) =>
      api(`/api/v1/universe/reminders/${id}/dismiss`, { method: "POST" }),
    scan: () =>
      api<{ created: number }>("/api/v1/universe/reminders/scan", { method: "POST" }),
  },
  preferences: {
    get: () => api<CareerPreferences | null>("/api/v1/universe/preferences"),
    set: (body: Partial<CareerPreferences>) =>
      api<CareerPreferences>("/api/v1/universe/preferences", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
  },
  search: (q: string, k = 10, types?: string[]) => {
    const qs = new URLSearchParams({ q, k: String(k) });
    if (types?.length) qs.set("types", types.join(","));
    return api<UniverseSearchHit[]>(`/api/v1/universe/search?${qs}`);
  },
  activity: (params?: { limit?: number; since?: string; types?: string[] }) => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.since) qs.set("since", params.since);
    if (params?.types?.length) qs.set("types", params.types.join(","));
    const qstr = qs.toString();
    return api<ActivityEvent[]>(`/api/v1/universe/activity${qstr ? `?${qstr}` : ""}`);
  },
};

export interface UniverseSearchHit {
  entity_type: string;
  entity_id: string;
  score: number;
  preview?: string | null;
  payload?: Record<string, unknown>;
}

export interface ActivityEvent {
  event_id: string;
  event_type: string;
  occurred_at: string;
  payload: Record<string, unknown>;
}

export interface CareerPreferences {
  status: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  contract_types: string[];
  remote_preference: string | null;
  open_to_relocate: boolean | null;
  working_areas: Array<Record<string, unknown>>;
  perks_must_have: string[];
  perks_nice_to_have: string[];
  preferred_competences: string[];
  discarded_competences: string[];
  preferred_roles: string[];
  discarded_roles: string[];
  motivations: string | null;
}

export interface ReminderRow {
  id: string;
  kind: string;
  subject_type: string | null;
  subject_id: string | null;
  title: string;
  body: string;
  due_at: string;
}

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

export interface CvParseCandidates {
  experience: Array<{
    organization: string;
    role: string;
    description?: string | null;
    start_date?: string | null;
    end_date?: string | null;
    is_current?: boolean;
  }>;
  education: Array<{
    institution: string;
    degree?: string | null;
    field_of_study?: string | null;
    start_date?: string | null;
    end_date?: string | null;
  }>;
  skills: Array<{ name: string; category?: string; level?: string | null }>;
}

export interface CvParseResult {
  candidates: CvParseCandidates;
  meta?: { pages: number; chars: number; total: number };
  error?: string;
}

export const jobs = {
  list: (status?: JobStatus) => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : "";
    return api<JobRow[]>(`/api/v1/jobs${qs}`);
  },
  create: (body: Partial<Pick<JobRow, "url" | "title" | "company_name" | "description_raw" | "status">>) =>
    api<JobRow>("/api/v1/jobs", { method: "POST", body: JSON.stringify(body) }),
  patch: (
    id: string,
    body: Partial<
      Pick<
        JobRow,
        | "status"
        | "notes"
        | "applied_at"
        | "next_action_at"
        | "title"
        | "company_name"
        | "url"
        | "position"
      >
    >,
  ) => api<JobRow>(`/api/v1/jobs/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  remove: (id: string) => api<void>(`/api/v1/jobs/${id}`, { method: "DELETE" }),
  computeScore: (id: string) =>
    api<JobRow>(`/api/v1/jobs/${id}/score`, { method: "POST" }),
  documents: (id: string) => api<JobDocument[]>(`/api/v1/jobs/${id}/documents`),
  reorder: (items: Array<{ id: string; position: number; status?: JobStatus }>) =>
    api<{ updated: number }>("/api/v1/jobs/reorder", {
      method: "POST",
      body: JSON.stringify({ items }),
    }),
};

export type JobStatus =
  | "interested"
  | "applied"
  | "interviewing"
  | "offer"
  | "rejected"
  | "archived";

export interface MatchBreakdown {
  match_score: number;
  dimensions: {
    skills: number | null;
    experience: number | null;
    education: number | null;
  };
  strengths: string[];
  gaps: string[];
  keyword_coverage: number | null;
  suggested_keywords: string[];
}

export interface JobRow {
  id: string;
  company_name: string | null;
  title: string | null;
  url: string | null;
  description_raw: string;
  ats_detected: string | null;
  created_at: string | null;
  status: JobStatus;
  notes: string | null;
  applied_at: string | null;
  /** Follow-up date; setting it creates a job_followup reminder. */
  next_action_at: string | null;
  match_score: number | null;
  /** Per-dimension breakdown cached on the job once /score has run. */
  match: MatchBreakdown | null;
  position: number | null;
}

export interface JobDocument {
  id: string;
  kind: string;
  template: string;
  language: string;
  created_at: string | null;
  has_pdf: boolean;
}

export const notes = {
  list: () => api<NoteRow[]>("/api/v1/notes"),
  create: (body: { title?: string | null; body_md: string; tags?: string[] }) =>
    api<NoteRow>("/api/v1/notes", { method: "POST", body: JSON.stringify(body) }),
  patch: (id: string, body: { title?: string | null; body_md?: string; tags?: string[] }) =>
    api<NoteRow>(`/api/v1/notes/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  remove: (id: string) => api<void>(`/api/v1/notes/${id}`, { method: "DELETE" }),
};

export interface NoteRow {
  id: string;
  title: string | null;
  body_md: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export const documents = {
  list: () => api<DocumentSummary[]>("/api/v1/documents"),
  get: (id: string) => api<DocumentDetail>(`/api/v1/documents/${id}`),
  generate: (b: {
    job_description?: string;
    job_url?: string;
    template?: string;
    language?: string;
    tone?: string;
    kind?: "cv" | "cover_letter";
  }) =>
    api<GenerateCvResponse>("/api/v1/documents/generate-cv", {
      method: "POST",
      body: JSON.stringify(b),
    }),
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
  source_entity_ids?: string[];
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
  /** Production checkout: backend returns a Stripe hosted URL; if Stripe is
   *  in mock mode the URL is a local /billing/checkout-mock?... we navigate
   *  to directly. */
  checkout: (plan: "premium" | "pro", returnUrl?: string) =>
    api<{ checkout_url: string }>("/api/v1/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan, return_url: returnUrl }),
    }),
  /** Stripe Customer Portal (manage card, cancel, see invoices). Only
   *  works if the user already has a Stripe customer id. */
  portal: (returnUrl?: string) =>
    api<{ portal_url: string }>("/api/v1/billing/portal", {
      method: "POST",
      body: JSON.stringify({ return_url: returnUrl }),
    }),
  cancel: () => api<SubscriptionDto>("/api/v1/billing/cancel", { method: "POST" }),
  /** Dev-only: simulates a Stripe webhook event. The backend rejects this
   *  in production. The frontend keeps using it when running against a
   *  dev/staging backend so the upgrade button works without real cards. */
  upgradeMock: (plan: "premium" | "pro") =>
    api<SubscriptionDto>("/api/v1/billing/webhook/test", {
      method: "POST",
      body: JSON.stringify({
        event: "checkout.completed",
        user_id: useAuthStore.getState().userId,
        plan,
      }),
      authRequired: false,
    }),
};

export interface McpStats {
  total_invocations: number;
  invocations_today: number;
  invocations_this_week: number;
  top_tools: { tool_name: string; count: number }[];
  recent_errors: number;
}

export const mcp = {
  stats: () => api<McpStats>("/api/v1/mcp/stats"),
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
