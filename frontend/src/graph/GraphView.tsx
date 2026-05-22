/**
 * GraphView — elevated sigma.js renderer for the user's professional universe.
 *
 * The universe graph is the product's signature surface, so it's styled as a
 * "constellation": nodes are haloed discs colour-coded by `kind`, sized by
 * degree centrality, with curved edges and an ego-network hover highlight
 * (hovering a node lifts it + its neighbours and dims the rest). A subtle
 * radial sky sits behind it.
 *
 * Two modes:
 *  • interactive (default) — labels, hover/click, zoom controls.
 *  • ambient — no labels/interaction, dimmed; used as the home backdrop
 *    behind the floating chat. Combined with a slow CSS drift on the wrapper.
 *
 * Layout: ForceAtlas2 on the main thread (typical universe < 200 nodes), with
 * a per-kind seeding pass so same-kind nodes settle into loose clusters.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import {
  SigmaContainer,
  useLoadGraph,
  useRegisterEvents,
  useSigma,
} from "@react-sigma/core";
import GraphCtor from "graphology";
import forceAtlas2 from "graphology-layout-forceatlas2";
import { NodeBorderProgram } from "@sigma/node-border";
import EdgeCurveProgram, { indexParallelEdgesIndex } from "@sigma/edge-curve";
import { Plus, Minus, Maximize2 } from "lucide-react";
import "@react-sigma/core/lib/style.css";
import type { GraphSnapshot } from "./api";
import { KIND_COLORS, DEFAULT_KIND_COLOR } from "@/shared/kindColors";

// Minimal structural type over the graphology instance methods we use.
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

/** Read a CSS custom property off :root (handles light/dark at build time). */
function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export interface GraphViewProps {
  snapshot: GraphSnapshot;
  onFocusEntity?: (entityId: string, kind: string, label: string) => void;
  kindsFilter?: string[];
  /** Backdrop mode: no labels/interaction, dimmed. */
  ambient?: boolean;
}

interface GraphLoaderProps {
  snapshot: GraphSnapshot;
  kindsFilter?: string[];
}

function GraphLoader({ snapshot, kindsFilter }: GraphLoaderProps) {
  const loadGraph = useLoadGraph();

  useEffect(() => {
    const g = new Graph({ multi: false, type: "directed" });
    const filtered =
      kindsFilter && kindsFilter.length > 0 ? new Set(kindsFilter) : null;

    // Stable per-kind anchor angle so same-kind nodes seed near each other
    // and ForceAtlas2 settles them into loose clusters.
    const kinds = Array.from(
      new Set(snapshot.nodes.map((n) => n.attributes.kind)),
    );
    const kindAngle = new Map<string, number>();
    kinds.forEach((k, i) => kindAngle.set(k, (i / Math.max(1, kinds.length)) * Math.PI * 2));

    const ringColor = cssVar("--hairline-strong", "rgba(10,10,10,0.14)");

    let placed = 0;
    snapshot.nodes.forEach((node) => {
      if (filtered && !filtered.has(node.attributes.kind)) return;
      const base = kindAngle.get(node.attributes.kind) ?? 0;
      const jitter = (placed % 7) * 0.18;
      const radius = 4 + Math.sqrt(placed + 1) * 1.4;
      placed += 1;
      g.addNode(node.key, {
        label: node.attributes.label,
        x: Math.cos(base + jitter) * radius,
        y: Math.sin(base + jitter) * radius,
        size: 9,
        color: KIND_COLORS[node.attributes.kind] ?? DEFAULT_COLOR,
        borderColor: ringColor,
        kind: node.attributes.kind,
        zIndex: 1,
      });
    });

    snapshot.edges.forEach((edge) => {
      if (!g.hasNode(edge.source) || !g.hasNode(edge.target)) return;
      try {
        g.addEdgeWithKey(edge.key, edge.source, edge.target, {
          size: 1.4,
          color: cssVar("--hairline-strong", "rgba(100,116,139,0.35)"),
          edge_type: edge.attributes.edge_type,
        });
      } catch {
        // Duplicate edge key — dedup guard.
      }
    });

    // Size nodes by degree centrality (more connected → bigger). Keep a
    // generous floor so even an unconnected universe reads as a constellation.
    g.forEachNode((node: string) => {
      const degree = g.degree(node);
      g.setNodeAttribute(node, "size", 9 + Math.sqrt(degree) * 2.6);
    });

    // Curvature for parallel edges so they don't overlap.
    try {
      indexParallelEdgesIndex(g as never, { edgeIndexAttribute: "curvature" });
    } catch {
      /* no edges or single edges — nothing to index */
    }

    type LoadableGraph = Parameters<typeof loadGraph>[0];
    if (g.order > 1) {
      forceAtlas2.assign(g as unknown as LoadableGraph, {
        iterations: g.order < 100 ? 120 : 60,
        settings: {
          gravity: 1.2,
          scalingRatio: 10,
          barnesHutOptimize: g.order > 100,
          adjustSizes: true,
        },
      });
    }

    loadGraph(g as unknown as LoadableGraph);
  }, [loadGraph, snapshot, kindsFilter]);

  return null;
}

interface GraphEventsProps {
  onFocusEntity?: GraphViewProps["onFocusEntity"];
  onSelect: (
    sel: { id: string; kind: string; label: string } | null,
  ) => void;
}

function GraphEvents({ onFocusEntity, onSelect }: GraphEventsProps) {
  const sigma = useSigma();
  const registerEvents = useRegisterEvents();
  const hovered = useRef<string | null>(null);
  const selected = useRef<string | null>(null);

  // Reducers read from refs and are installed once; hover/click just flip the
  // refs + refresh, so we never rebuild the settings object.
  useEffect(() => {
    const graph = sigma.getGraph();

    sigma.setSetting("nodeReducer", (node, data) => {
      const res = { ...data } as Record<string, unknown>;
      const focus = hovered.current ?? selected.current;
      if (focus) {
        const isFocus = node === focus;
        const isNeighbor = graph.areNeighbors(focus, node);
        if (isFocus) {
          res.highlighted = true;
          res.zIndex = 3;
          res.size = (data.size as number) * 1.15;
        } else if (isNeighbor) {
          res.zIndex = 2;
        } else {
          res.color = cssVar("--hairline-strong", "rgba(10,10,10,0.12)");
          res.label = "";
          res.zIndex = 0;
        }
      }
      return res;
    });

    sigma.setSetting("edgeReducer", (edge, data) => {
      const res = { ...data } as Record<string, unknown>;
      const focus = hovered.current ?? selected.current;
      if (focus) {
        const [s, t] = graph.extremities(edge);
        if (s === focus || t === focus) {
          res.color = cssVar("--color-leafy-green", "#6ece9d");
          res.size = (data.size as number) * 1.8;
          res.zIndex = 2;
        } else {
          res.hidden = true;
        }
      }
      return res;
    });

    registerEvents({
      enterNode: ({ node }) => {
        hovered.current = node;
        sigma.getContainer().style.cursor = "pointer";
        sigma.refresh({ skipIndexation: true });
      },
      leaveNode: () => {
        hovered.current = null;
        sigma.getContainer().style.cursor = "default";
        sigma.refresh({ skipIndexation: true });
      },
      clickNode: ({ node }) => {
        selected.current = node;
        const attrs = sigma.getGraph().getNodeAttributes(node) as Record<string, unknown>;
        const kind = (attrs.kind as string) ?? "entity";
        const label = (attrs.label as string) ?? node;
        onSelect({ id: node, kind, label });
        onFocusEntity?.(node, kind, label);
        sigma.refresh({ skipIndexation: true });
      },
      clickStage: () => {
        selected.current = null;
        onSelect(null);
        sigma.refresh({ skipIndexation: true });
      },
    });
  }, [sigma, registerEvents, onFocusEntity, onSelect]);

  return null;
}

function ZoomControls() {
  const sigma = useSigma();
  const camera = sigma.getCamera();
  const btn =
    "grid place-items-center w-8 h-8 rounded-btn bg-canvas/90 backdrop-blur border border-hairline text-stone hover:text-ink hover:bg-canvas transition-colors duration-180 shadow-soft";
  return (
    <div className="absolute bottom-3 right-3 flex flex-col gap-1.5">
      <button type="button" aria-label="Acercar" className={btn}
        onClick={() => camera.animatedZoom({ duration: 280 })}>
        <Plus size={15} />
      </button>
      <button type="button" aria-label="Alejar" className={btn}
        onClick={() => camera.animatedUnzoom({ duration: 280 })}>
        <Minus size={15} />
      </button>
      <button type="button" aria-label="Centrar" className={btn}
        onClick={() => camera.animatedReset({ duration: 320 })}>
        <Maximize2 size={14} />
      </button>
    </div>
  );
}

export function GraphView({
  snapshot,
  onFocusEntity,
  kindsFilter,
  ambient = false,
}: GraphViewProps) {
  const [selected, setSelected] = useState<
    { id: string; kind: string; label: string } | null
  >(null);

  const settings = useMemo(
    () => ({
      nodeProgramClasses: { border: NodeBorderProgram },
      edgeProgramClasses: { curved: EdgeCurveProgram },
      defaultNodeType: "border",
      defaultEdgeType: "curved",
      renderLabels: !ambient,
      renderEdgeLabels: false,
      labelFont: '"DM Sans", system-ui, sans-serif',
      labelSize: 12.5,
      labelWeight: "500",
      labelColor: { color: cssVar("--color-midnight-ink", "#0a0a0a") },
      labelDensity: 1,
      labelGridCellSize: 60,
      labelRenderedSizeThreshold: ambient ? Number.POSITIVE_INFINITY : 0,
      defaultNodeColor: DEFAULT_COLOR,
      zIndex: true,
      allowInvalidContainer: true,
      enableEdgeEvents: false,
    }),
    [ambient],
  );

  if (snapshot.node_count === 0 && !ambient) {
    return null; // empty state handled by the page (constellation placeholder)
  }

  return (
    <div className="relative h-full w-full">
      <SigmaContainer
        style={{ height: "100%", width: "100%", background: "transparent" }}
        settings={settings}
        className={ambient ? "pointer-events-none opacity-70" : undefined}
      >
        <GraphLoader snapshot={snapshot} kindsFilter={kindsFilter} />
        {!ambient && (
          <>
            <GraphEvents onFocusEntity={onFocusEntity} onSelect={setSelected} />
            <ZoomControls />
          </>
        )}
      </SigmaContainer>

      {!ambient && selected && (
        <div className="absolute top-3 left-3 max-w-xs rounded-card bg-canvas/95 backdrop-blur shadow-float border border-hairline px-4 py-3">
          <p className="eyebrow mb-1">{selected.kind}</p>
          <p className="font-display text-[17px] leading-tight text-ink break-words">
            {selected.label}
          </p>
          {onFocusEntity && (
            <button
              type="button"
              onClick={() => onFocusEntity(selected.id, selected.kind, selected.label)}
              className="mt-2 text-xs font-medium text-leaf-ink hover:underline"
            >
              Hablar de esto →
            </button>
          )}
        </div>
      )}
    </div>
  );
}
