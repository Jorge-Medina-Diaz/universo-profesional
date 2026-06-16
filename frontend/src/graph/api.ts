/**
 * Thin client for the `/api/v1/graph/*` REST surface.
 */
import { api } from "@/shared/api";

export interface GraphNode {
  key: string;
  attributes: {
    kind: string;
    label: string;
    /** Semantic area (backend/frontend/cloud/ai_ml/…); null if unmatched. */
    area?: string | null;
    /** Career pillar (Leiden community label); null until communities computed. */
    pillar?: string | null;
    /** ESCO ontology URI when the entity is linked. */
    esco_uri?: string | null;
    [k: string]: unknown;
  };
}

export interface CareerPillar {
  id: string;
  label: string;
  summary: string;
  size: number;
  members: string[];
}

export interface GraphEdge {
  key: string;
  source: string;
  target: string;
  attributes: {
    edge_type: string;
    confidence?: number | null;
    [k: string]: unknown;
  };
}

export interface GraphSnapshot {
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
}

export interface DiscoveryStreamEvent {
  type: "entity_discovered";
  entity_type: string;
  name: string;
  source: string;
}

export const graphApi = {
  snapshot: async (includeExpired = false): Promise<GraphSnapshot> =>
    api<GraphSnapshot>(
      `/api/v1/graph/snapshot?include_expired=${includeExpired ? "true" : "false"}`,
    ),

  discoveryStreamURL: "/api/v1/agents/discovery/stream" as const,

  neighbors: async (
    entityId: string,
    opts: { depth?: number; includeExpired?: boolean } = {},
  ): Promise<{ items: Record<string, unknown>[]; count: number }> => {
    const params = new URLSearchParams();
    if (opts.depth) params.set("depth", String(opts.depth));
    if (opts.includeExpired) params.set("include_expired", "true");
    return api(`/api/v1/graph/entity/${entityId}/neighbors?${params}`);
  },

  enrich: async (): Promise<{ status: string; stats: Record<string, number> }> =>
    api("/api/v1/graph/enrich", { method: "POST" }),

  communities: async (): Promise<{ items: CareerPillar[]; count: number }> =>
    api("/api/v1/graph/communities"),
};
