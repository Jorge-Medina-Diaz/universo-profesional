/**
 * GraphView — sigma.js renderer for the user's personal universe.
 *
 * Renders the AGE personal graph as a 2-D force-directed layout. Nodes
 * are colour-coded by `kind`; sizes scale with degree centrality. Click
 * a node to surface its details + a "talk about this" callback that the
 * parent uses to set the chat focus.
 *
 * Layout strategy: ForceAtlas2 runs on the main thread for graphs
 * under 200 nodes (typical universe size); larger graphs would benefit
 * from the dedicated worker variant but that requires wiring a
 * worker-loader plugin — deferred to Sprint R perf pass.
 */
import { useEffect, useMemo, useState } from "react";
import {
  SigmaContainer,
  useLoadGraph,
  useRegisterEvents,
  useSigma,
} from "@react-sigma/core";
import GraphCtor from "graphology";
import forceAtlas2 from "graphology-layout-forceatlas2";
import "@react-sigma/core/lib/style.css";
import type { GraphSnapshot } from "./api";
import { KIND_COLORS, DEFAULT_KIND_COLOR } from "@/shared/kindColors";

// Minimal structural type over the graphology instance methods we use.
// graphology's bundled .d.ts re-exports an interface that drops the
// constructor overload + instance methods, so we narrow to exactly the
// surface this file touches and cast the constructor once.
interface GraphLike {
  order: number;
  addNode(key: string, attrs: Record<string, unknown>): void;
  hasNode(key: string): boolean;
  addEdgeWithKey(
    key: string,
    source: string,
    target: string,
    attrs: Record<string, unknown>,
  ): void;
  forEachNode(cb: (node: string, attrs: Record<string, unknown>) => void): void;
  degree(node: string): number;
  setNodeAttribute(node: string, name: string, value: unknown): void;
}
type GraphCtorType = new (opts?: {
  multi?: boolean;
  type?: "directed" | "undirected" | "mixed";
}) => GraphLike;
const Graph = GraphCtor as unknown as GraphCtorType;

const DEFAULT_COLOR = DEFAULT_KIND_COLOR;

export interface GraphViewProps {
  snapshot: GraphSnapshot;
  /** Called when the user clicks a node and chooses "talk about this". */
  onFocusEntity?: (
    entityId: string,
    kind: string,
    label: string,
  ) => void;
  /** Filter to only certain kinds; empty/undefined shows everything. */
  kindsFilter?: string[];
}

interface GraphLoaderProps {
  snapshot: GraphSnapshot;
  kindsFilter?: string[];
}

function GraphLoader({ snapshot, kindsFilter }: GraphLoaderProps) {
  const loadGraph = useLoadGraph();

  useEffect(() => {
    const g = new Graph({ multi: false, type: "directed" });
    const filtered = kindsFilter && kindsFilter.length > 0
      ? new Set(kindsFilter)
      : null;

    // Vertex placement: a sunflower seed pattern for a stable initial
    // layout, then ForceAtlas2 untangles it.
    snapshot.nodes.forEach((node, idx) => {
      if (filtered && !filtered.has(node.attributes.kind)) return;
      const angle = idx * 2.3998; // golden angle
      const radius = Math.sqrt(idx + 1) * 3;
      g.addNode(node.key, {
        label: node.attributes.label,
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
        size: 5,
        color: KIND_COLORS[node.attributes.kind] ?? DEFAULT_COLOR,
        kind: node.attributes.kind,
      });
    });

    snapshot.edges.forEach((edge) => {
      if (!g.hasNode(edge.source) || !g.hasNode(edge.target)) return;
      try {
        g.addEdgeWithKey(
          edge.key,
          edge.source,
          edge.target,
          {
            label: edge.attributes.edge_type,
            size: 1,
            color: "rgba(100, 116, 139, 0.35)",
            edge_type: edge.attributes.edge_type,
          },
        );
      } catch {
        // Duplicate edge key — graphology rejects; the BM25/PPR layers
        // already deduplicate, but we double-guard here for safety.
      }
    });

    // Size nodes by degree centrality (more connected → bigger).
    g.forEachNode((node: string) => {
      const degree = g.degree(node);
      g.setNodeAttribute(node, "size", 4 + Math.sqrt(degree) * 2);
    });

    // ForceAtlas2 — synchronous; deferred to a worker in Sprint R for >500 nodes.
    // `g` is narrowed to GraphLike (see note above); cast to the graphology
    // Graph type the layout + loader expect.
    type LoadableGraph = Parameters<typeof loadGraph>[0];
    if (g.order > 1) {
      forceAtlas2.assign(g as unknown as LoadableGraph, {
        iterations: g.order < 100 ? 80 : 50,
        settings: {
          gravity: 1,
          scalingRatio: 8,
          barnesHutOptimize: g.order > 100,
        },
      });
    }

    loadGraph(g as unknown as LoadableGraph);
  }, [loadGraph, snapshot, kindsFilter]);

  return null;
}

interface GraphInteractionProps {
  onFocusEntity?: GraphViewProps["onFocusEntity"];
}

function GraphInteraction({ onFocusEntity }: GraphInteractionProps) {
  const registerEvents = useRegisterEvents();
  const sigma = useSigma();
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    registerEvents({
      clickNode: (event) => {
        setSelected(event.node);
        const graph = sigma.getGraph();
        const attrs = graph.getNodeAttributes(event.node);
        onFocusEntity?.(
          event.node,
          (attrs.kind as string) ?? "entity",
          (attrs.label as string) ?? event.node,
        );
      },
      clickStage: () => setSelected(null),
    });
  }, [registerEvents, sigma, onFocusEntity]);

  return selected ? (
    <div className="absolute top-3 right-3 max-w-xs rounded-card bg-surface/95 backdrop-blur shadow-soft border border-ink/[0.08] px-4 py-3 text-sm">
      <p className="text-xs uppercase tracking-wide text-ink/40">
        seleccionado
      </p>
      <p className="font-medium text-ink mt-1 break-words">
        {sigma.getGraph().getNodeAttribute(selected, "label") as string}
      </p>
      <p className="text-xs text-ink/60 mt-0.5">
        {sigma.getGraph().getNodeAttribute(selected, "kind") as string}
      </p>
    </div>
  ) : null;
}

export function GraphView({
  snapshot,
  onFocusEntity,
  kindsFilter,
}: GraphViewProps) {
  const settings = useMemo(
    () => ({
      renderEdgeLabels: false,
      defaultNodeColor: DEFAULT_COLOR,
      labelDensity: 0.6,
      labelGridCellSize: 80,
      labelRenderedSizeThreshold: 5,
    }),
    [],
  );

  if (snapshot.node_count === 0) {
    return (
      <div className="flex h-full w-full items-center justify-center text-ink/50 text-sm">
        Tu universo todavía está vacío — empieza una conversación.
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <SigmaContainer
        style={{ height: "100%", width: "100%", background: "transparent" }}
        settings={settings}
      >
        <GraphLoader snapshot={snapshot} kindsFilter={kindsFilter} />
        <GraphInteraction onFocusEntity={onFocusEntity} />
      </SigmaContainer>
    </div>
  );
}

