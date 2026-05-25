/**
 * Data hooks for the graph node-detail drawer.
 *
 * The graph snapshot only carries {kind,label}; rich content is fetched lazily
 * on click. We reuse the per-kind list endpoints (`GET /api/v1/universe/{kind}`)
 * — which return full ORM rows — and find the entity by id (cached per kind, so
 * navigating between same-kind nodes is instant). Documents use their own
 * endpoint. Neighbors come from the graph service.
 */
import { useQuery } from "@tanstack/react-query";
import { universe, documents, type DocumentDetail } from "@/shared/api";
import { graphApi } from "./api";

export type EntityRow = Record<string, unknown> & { id: string };

/** Kinds with a `GET /api/v1/universe/{kind}` list endpoint. */
const LIST_KINDS = new Set([
  "education",
  "experience",
  "project",
  "skill",
  "certification",
  "course",
  "language",
  "achievement",
  "interest",
]);

export function kindHasDetail(kind: string): boolean {
  return LIST_KINDS.has(kind) || kind === "document";
}

export interface EntityDetail {
  kind: string;
  row: EntityRow | null;
  document: DocumentDetail | null;
}

/** Strip the synthetic `doc-` prefix the universe overlay adds to doc nodes. */
export function rawEntityId(nodeId: string): string {
  return nodeId.replace(/^doc-/, "");
}

export function useEntityDetail(kind: string | null, nodeId: string | null) {
  return useQuery<EntityDetail | null>({
    queryKey: ["entity-detail", kind, nodeId],
    enabled: !!kind && !!nodeId,
    staleTime: 30_000,
    queryFn: async () => {
      if (!kind || !nodeId) return null;
      if (kind === "document") {
        const doc = await documents.get(rawEntityId(nodeId));
        return { kind, row: null, document: doc };
      }
      if (!LIST_KINDS.has(kind)) return { kind, row: null, document: null };
      const rows = (await universe.list(kind)) as EntityRow[];
      const row = rows.find((r) => String(r.id) === nodeId) ?? null;
      return { kind, row, document: null };
    },
  });
}

export interface NeighborRow extends Record<string, unknown> {
  id?: string;
  kind?: string;
}

export function useNeighbors(nodeId: string | null, depth = 1) {
  return useQuery<NeighborRow[]>({
    queryKey: ["entity-neighbors", nodeId, depth],
    enabled: !!nodeId && !nodeId.startsWith("doc-"),
    staleTime: 30_000,
    // The neighbors endpoint can 500 on graphs with no edges; fail fast and
    // let the drawer hide the section rather than retry-spamming.
    retry: false,
    queryFn: async () => {
      if (!nodeId) return [];
      const res = await graphApi.neighbors(nodeId, { depth });
      return (res.items ?? []) as NeighborRow[];
    },
  });
}
