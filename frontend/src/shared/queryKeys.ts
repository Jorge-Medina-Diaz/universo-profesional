/**
 * Centralized TanStack Query keys to prevent string-literal duplication
 * and make invalidation refactoring trivial.
 */
export const queryKeys = {
  universe: {
    all: ["universe"] as const,
    summary: ["universe", "summary"] as const,
    shape: ["universe", "shape"] as const,
    preferences: ["universe", "preferences"] as const,
  },
  jobs: {
    all: ["jobs"] as const,
    detail: (id?: string) => ["jobs", id] as const,
  },
  documents: {
    all: ["documents"] as const,
    detail: (id?: string) => ["documents", id] as const,
  },
  reminders: {
    all: ["reminders"] as const,
    pending: ["reminders", "pending"] as const,
  },
  nudges: {
    active: ["nudges", "active"] as const,
  },
  suggestions: {
    all: ["suggestions"] as const,
    pending: ["suggestions", "pending"] as const,
  },
  coherence: {
    changes: ["coherence", "changes"] as const,
  },
  integrations: {
    all: ["integrations"] as const,
    status: ["integrations", "status"] as const,
    list: ["integrations", "list"] as const,
    syncRuns: ["integrations", "sync-runs"] as const,
  },
  graph: {
    all: ["graph"] as const,
    snapshot: ["graph", "snapshot"] as const,
    communities: ["graph", "communities"] as const,
    neighbors: (id?: string) => ["graph", "neighbors", id] as const,
  },
  auth: {
    me: ["auth", "me"] as const,
  },
  me: {
    all: ["me"] as const,
    photo: (refreshKey?: number) => ["me", "photo", refreshKey] as const,
  },
  preferences: {
    all: ["preferences"] as const,
  },
  chat: {
    state: ["chat", "state"] as const,
  },
  palette: {
    search: (q?: string) => ["palette-search", q] as const,
  },
  entity: {
    detail: (kind?: string | null, nodeId?: string | null) => ["entity-detail", kind, nodeId] as const,
    neighbors: (nodeId?: string | null, depth?: number) => ["entity-neighbors", nodeId, depth] as const,
  },
  linkedin: {
    probe: ["linkedin-probe"] as const,
    status: ["linkedin-status"] as const,
  },
  trajectory: {
    all: ["trajectory"] as const,
  },
  activity: {
    list: (filter?: string) => ["activity", filter] as const,
  },
  notes: {
    all: ["notes"] as const,
  },
  billing: {
    plans: ["billing", "plans"] as const,
    subscription: ["billing", "subscription"] as const,
  },
  connections: {
    all: ["connections"] as const,
  },
  syncRuns: {
    all: ["syncRuns"] as const,
  },
  share: {
    detail: (token?: string) => ["share", token] as const,
  },
  goals: {
    all: ["goals"] as const,
  },
  artifacts: {
    all: ["artifacts"] as const,
  },
  architectureDecisions: {
    all: ["architecture_decisions"] as const,
  },
  agents: {
    discovery: {
      progress: ["agents", "discovery", "progress"] as const,
    },
  },
  llm: {
    usage: ["llm", "usage"] as const,
    sessions: ["llm", "sessions"] as const,
  },
  mcp: {
    stats: ["mcp", "stats"] as const,
  },
} as const;
