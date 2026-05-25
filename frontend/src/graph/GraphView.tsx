/**
 * GraphView — elevated sigma.js renderer for the user's professional universe.
 *
 * The universe is the product's signature surface: a navigable "constellation"
 * where nodes are grouped into **semantic area islands** (backend, frontend,
 * cloud, IA, datos…). Colour encodes the AREA (the cluster) and the white
 * pictogram encodes the entity KIND — so a hued region with mixed glyphs reads
 * as "my backend stack: these skills, that project, this role". Hovering lifts a
 * node + its neighbours (ego-network) and dims the rest; clicking animates the
 * camera to focus it and opens the floating inspector. Nodes are draggable.
 *
 * Two modes:
 *  • interactive (default) — pictograms, labels, area labels, hover/click/drag,
 *    camera focus, zoom controls.
 *  • ambient — no labels/interaction, dimmed; used as the home backdrop behind
 *    the floating chat.
 *
 * Layout is deterministic (area islands + phyllotaxis + seeded jitter) rather
 * than force-driven: the personal graph's edges are mostly document-overlay
 * links, which a global ForceAtlas2 would collapse the whole map around. Stable
 * islands keep the areas coherent and the map "self-explanatory".
 */
import { useEffect, useMemo, useRef } from "react";
import {
  SigmaContainer,
  useLoadGraph,
  useRegisterEvents,
  useSigma,
} from "@react-sigma/core";
import GraphCtor from "graphology";
import { NodeBorderProgram } from "@sigma/node-border";
import { createNodeImageProgram } from "@sigma/node-image";
import EdgeCurveProgram, { indexParallelEdgesIndex } from "@sigma/edge-curve";
import { Plus, Minus, Maximize2 } from "lucide-react";
import "@react-sigma/core/lib/style.css";
import type { GraphSnapshot } from "./api";
import { areaKey, colorForArea, labelForArea } from "@/shared/areaColors";
import { iconFor, edgeLabel } from "./nodeIcons";

// Built once: colored disc background + white pictogram drawn on top, clipped
// to the circle. Texture is shared across this module's sigma instances.
const NodeImageProgram = createNodeImageProgram({
  drawingMode: "background",
  keepWithinCircle: true,
  padding: 0.28,
});

interface GraphLike {
  order: number;
  size: number;
  addNode(key: string, attrs: Record<string, unknown>): void;
  hasNode(key: string): boolean;
  addEdgeWithKey(key: string, source: string, target: string, attrs: Record<string, unknown>): void;
  forEachNode(cb: (node: string, attrs: Record<string, unknown>) => void): void;
  degree(node: string): number;
  setNodeAttribute(node: string, name: string, value: unknown): void;
}
type GraphCtorType = new (opts?: {
  multi?: boolean;
  type?: "directed" | "undirected" | "mixed";
}) => GraphLike;
const Graph = GraphCtor as unknown as GraphCtorType;

/** Read a CSS custom property off :root (handles light/dark). */
function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

/** Stable [0,1) pseudo-random from a string — keeps jitter constant per node. */
function seeded(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 100000) / 100000;
}

/** Overlay edges (document → entity provenance) recede; they don't cluster. */
const OVERLAY_EDGE = "generated_from";

interface ThemeColors {
  ink: string;
  stone: string;
  dim: string;
  leaf: string;
  edge: string;
}
function readColors(): ThemeColors {
  return {
    ink: cssVar("--color-midnight-ink", "#0a0a0a"),
    stone: cssVar("--color-muted-stone", "#6b7280"),
    dim: cssVar("--hairline-strong", "rgba(10,10,10,0.12)"),
    leaf: cssVar("--color-leafy-green", "#6ece9d"),
    edge: cssVar("--hairline", "rgba(10,10,10,0.08)"),
  };
}

export interface GraphSelection {
  id: string;
  kind: string;
  label: string;
}

export interface GraphViewProps {
  snapshot: GraphSnapshot;
  kindsFilter?: string[];
  /** Backdrop mode: no labels/interaction, dimmed. */
  ambient?: boolean;
  /** Controlled selection (highlights node + focuses camera). */
  selectedId?: string | null;
  /** Fired on node click / stage click (null). Parent opens the inspector. */
  onSelectEntity?: (sel: GraphSelection | null) => void;
}

function GraphLoader({
  snapshot,
  kindsFilter,
}: {
  snapshot: GraphSnapshot;
  kindsFilter?: string[];
}) {
  const loadGraph = useLoadGraph();

  useEffect(() => {
    const g = new Graph({ multi: false, type: "directed" });
    const filtered = kindsFilter && kindsFilter.length > 0 ? new Set(kindsFilter) : null;

    const visible = snapshot.nodes.filter((n) => !filtered || filtered.has(n.attributes.kind));

    // Group by SEMANTIC AREA so each area becomes a coherent, labeled island.
    const byArea = new Map<string, typeof visible>();
    for (const n of visible) {
      const ak = areaKey(n.attributes.area, n.attributes.kind);
      const list = byArea.get(ak) ?? [];
      list.push(n);
      byArea.set(ak, list);
    }
    // Largest area is the core of the universe; the rest orbit it. This fills
    // the centre (no empty donut) and reads as "this is what you're about".
    const areas = Array.from(byArea.keys()).sort(
      (a, b) => (byArea.get(b)?.length ?? 0) - (byArea.get(a)?.length ?? 0),
    );
    const islandRadius = (n: number) => 0.95 * Math.sqrt(Math.max(1, n));

    const placeIsland = (ak: string, cx: number, cy: number) => {
      const color = colorForArea(ak);
      const nodes = byArea.get(ak) ?? [];
      nodes.forEach((node, i) => {
        // Phyllotaxis spiral → even, organic packing; seeded jitter adds life.
        const a = i * 2.399963;
        const r = 0.95 * Math.sqrt(i);
        const jx = (seeded(node.key + "x") - 0.5) * 0.6;
        const jy = (seeded(node.key + "y") - 0.5) * 0.6;
        g.addNode(node.key, {
          type: "image",
          image: iconFor(node.attributes.kind),
          label: node.attributes.label,
          x: cx + Math.cos(a) * r + jx,
          y: cy + Math.sin(a) * r + jy,
          size: 16,
          color,
          kind: node.attributes.kind,
          areaKey: ak,
          zIndex: 1,
        });
      });
    };

    const coreCount = byArea.get(areas[0])?.length ?? 0;
    const satellites = areas.slice(1);
    // Orbit distance: clear the core island + the biggest satellite + a gap.
    const maxSatellite = Math.max(1, ...satellites.map((a) => byArea.get(a)?.length ?? 0));
    const ring = islandRadius(coreCount) + islandRadius(maxSatellite) + 5.5;

    if (areas.length > 0) placeIsland(areas[0], 0, 0);
    satellites.forEach((ak, si) => {
      const angle = (si / Math.max(1, satellites.length)) * Math.PI * 2 - Math.PI / 2;
      placeIsland(ak, Math.cos(angle) * ring, Math.sin(angle) * ring);
    });

    const edgeColor = cssVar("--hairline", "rgba(10,10,10,0.08)");
    snapshot.edges.forEach((edge) => {
      if (!g.hasNode(edge.source) || !g.hasNode(edge.target)) return;
      const conf = typeof edge.attributes.confidence === "number" ? edge.attributes.confidence : 0.3;
      const overlay = edge.attributes.edge_type === OVERLAY_EDGE;
      try {
        g.addEdgeWithKey(edge.key, edge.source, edge.target, {
          size: overlay ? 0.7 : 1 + conf * 2.2,
          color: edgeColor,
          edge_type: edge.attributes.edge_type,
        });
      } catch {
        /* duplicate edge key — dedup guard */
      }
    });

    // Size by degree centrality — hubs read bigger. Generous floor so a
    // disconnected universe stays legible.
    g.forEachNode((node: string) => {
      const degree = g.degree(node);
      g.setNodeAttribute(node, "size", 16 + Math.sqrt(degree) * 3.4);
    });

    try {
      indexParallelEdgesIndex(g as never, { edgeIndexAttribute: "curvature" });
    } catch {
      /* no parallel edges */
    }

    type LoadableGraph = Parameters<typeof loadGraph>[0];
    loadGraph(g as unknown as LoadableGraph);
  }, [loadGraph, snapshot, kindsFilter]);

  return null;
}

/** Floating DOM labels at each area-island centroid, synced to the camera. */
function ClusterLabels({ signature }: { signature: string }) {
  const sigma = useSigma();
  const layerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const graph = sigma.getGraph();
    const layer = layerRef.current;
    if (!layer) return;

    const els = new Map<string, HTMLDivElement>();

    const centroids = (): { ak: string; x: number; y: number }[] => {
      const acc = new Map<string, { x: number; y: number; n: number }>();
      graph.forEachNode((_node, attr) => {
        const ak = (attr.areaKey as string) ?? "";
        if (!ak) return;
        const cur = acc.get(ak) ?? { x: 0, y: 0, n: 0 };
        cur.x += attr.x as number;
        cur.y += attr.y as number;
        cur.n += 1;
        acc.set(ak, cur);
      });
      return Array.from(acc.entries())
        .filter(([, v]) => v.n > 0)
        .map(([ak, v]) => ({ ak, x: v.x / v.n, y: v.y / v.n }));
    };

    const update = () => {
      const seen = new Set<string>();
      for (const c of centroids()) {
        seen.add(c.ak);
        let el = els.get(c.ak);
        if (!el) {
          el = document.createElement("div");
          el.className = "cluster-label";
          el.textContent = labelForArea(c.ak);
          el.style.setProperty("--cl-color", colorForArea(c.ak));
          layer.appendChild(el);
          els.set(c.ak, el);
        }
        const p = sigma.graphToViewport({ x: c.x, y: c.y });
        el.style.transform = `translate(-50%, -50%) translate(${p.x}px, ${p.y}px)`;
      }
      for (const [ak, el] of els) {
        if (!seen.has(ak)) {
          el.remove();
          els.delete(ak);
        }
      }
    };

    update();
    sigma.on("afterRender", update);
    return () => {
      sigma.off("afterRender", update);
      els.forEach((el) => el.remove());
      els.clear();
    };
  }, [sigma, signature]);

  return <div ref={layerRef} className="cluster-labels-layer" aria-hidden />;
}

interface CaptorCoords {
  x: number;
  y: number;
  original: MouseEvent | TouchEvent;
  preventSigmaDefault: () => void;
}

function GraphEvents({
  selectedId,
  onSelectEntity,
}: {
  selectedId?: string | null;
  onSelectEntity?: (sel: GraphSelection | null) => void;
}) {
  const sigma = useSigma();
  const registerEvents = useRegisterEvents();
  const hovered = useRef<string | null>(null);
  const selected = useRef<string | null>(selectedId ?? null);
  const firstRun = useRef(true);
  const colors = useRef<ThemeColors>(readColors());
  const dragged = useRef<string | null>(null);
  const dragging = useRef(false);
  const dragMoved = useRef(false);

  // Install reducers once; hover/selection flip refs + refresh. Theme colours
  // are read from a ref so a live theme switch updates them without re-install.
  useEffect(() => {
    const graph = sigma.getGraph();

    sigma.setSetting("nodeReducer", (node, data) => {
      const res = { ...data } as Record<string, unknown>;
      const focus = hovered.current ?? selected.current;
      if (focus && graph.hasNode(focus)) {
        if (node === focus) {
          res.highlighted = true;
          res.zIndex = 3;
          res.size = (data.size as number) * 1.28;
        } else if (graph.areNeighbors(focus, node)) {
          res.zIndex = 2;
        } else {
          res.color = colors.current.dim;
          res.image = undefined;
          res.label = "";
          res.zIndex = 0;
        }
      }
      return res;
    });

    sigma.setSetting("edgeReducer", (edge, data) => {
      const res = { ...data } as Record<string, unknown>;
      const focus = hovered.current ?? selected.current;
      if (focus && graph.hasNode(focus)) {
        const [s, t] = graph.extremities(edge);
        if (s === focus || t === focus) {
          res.color = colors.current.leaf;
          res.size = (data.size as number) * 1.8;
          res.zIndex = 2;
          res.label = edgeLabel(data.edge_type as string | undefined);
        } else {
          res.hidden = true;
        }
      } else {
        // Resting state: hide document-provenance overlay edges so the map
        // breathes; they reappear when you hover/select a connected node.
        if (data.edge_type === OVERLAY_EDGE) res.hidden = true;
        res.label = "";
      }
      return res;
    });

    const setCursor = (c: string) => {
      sigma.getContainer().style.cursor = c;
    };

    registerEvents({
      enterNode: ({ node }) => {
        if (dragging.current) return;
        hovered.current = node;
        setCursor("grab");
        sigma.refresh({ skipIndexation: true });
      },
      leaveNode: () => {
        if (dragging.current) return;
        hovered.current = null;
        setCursor("default");
        sigma.refresh({ skipIndexation: true });
      },
      downNode: ({ node }) => {
        dragging.current = true;
        dragged.current = node;
        dragMoved.current = false;
        hovered.current = node;
        setCursor("grabbing");
        if (!sigma.getCustomBBox()) sigma.setCustomBBox(sigma.getBBox());
      },
      // Body-level move so the drag keeps working past the node's hit area.
      mousemovebody: (e: CaptorCoords) => {
        if (!dragging.current || !dragged.current) return;
        const pos = sigma.viewportToGraph(e);
        graph.setNodeAttribute(dragged.current, "x", pos.x);
        graph.setNodeAttribute(dragged.current, "y", pos.y);
        dragMoved.current = true;
        // Stop the camera from panning while we drag the node.
        e.preventSigmaDefault();
        e.original.preventDefault();
        e.original.stopPropagation();
      },
      mouseup: () => {
        if (dragged.current) {
          dragging.current = false;
          dragged.current = null;
          setCursor("default");
          sigma.refresh({ skipIndexation: true });
        }
      },
      mousedown: () => {
        if (!sigma.getCustomBBox()) sigma.setCustomBBox(sigma.getBBox());
      },
      clickNode: ({ node }) => {
        // A drag ends with a click event — swallow it so we don't open the
        // inspector after repositioning a node.
        if (dragMoved.current) {
          dragMoved.current = false;
          return;
        }
        const attrs = sigma.getGraph().getNodeAttributes(node) as Record<string, unknown>;
        const kind = (attrs.kind as string) ?? "entity";
        const label = (attrs.label as string) ?? node;
        onSelectEntity?.({ id: node, kind, label });
      },
      clickStage: () => {
        onSelectEntity?.(null);
      },
    });
  }, [sigma, registerEvents, onSelectEntity]);

  // Live theme switch: refresh cached colours + label colours, then repaint.
  useEffect(() => {
    const apply = () => {
      colors.current = readColors();
      sigma.setSetting("labelColor", { color: colors.current.ink });
      sigma.setSetting("edgeLabelColor", { color: colors.current.stone });
      sigma.refresh({ skipIndexation: true });
    };
    const obs = new MutationObserver(apply);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, [sigma]);

  // React to controlled selection: highlight + animate camera to the node.
  // Skip the camera move on the very first run (mount / lens-switch) — node
  // display data isn't laid out yet, which would fling the camera to (0,0).
  useEffect(() => {
    selected.current = selectedId ?? null;
    const graph = sigma.getGraph();
    if (firstRun.current) {
      firstRun.current = false;
      sigma.refresh({ skipIndexation: true });
      return;
    }
    if (selectedId && graph.hasNode(selectedId)) {
      const raf = requestAnimationFrame(() => {
        const display = sigma.getNodeDisplayData(selectedId);
        if (display && (display.x !== 0 || display.y !== 0)) {
          sigma.getCamera().animate(
            { x: display.x, y: display.y, ratio: Math.min(sigma.getCamera().ratio, 0.5) },
            { duration: 450 },
          );
        }
        sigma.refresh({ skipIndexation: true });
      });
      return () => cancelAnimationFrame(raf);
    }
    sigma.refresh({ skipIndexation: true });
  }, [sigma, selectedId]);

  return null;
}

function ZoomControls() {
  const sigma = useSigma();
  const camera = sigma.getCamera();
  const btn =
    "grid place-items-center w-9 h-9 rounded-btn bg-canvas/80 backdrop-blur border border-hairline text-stone hover:text-ink hover:bg-canvas transition-colors duration-180 shadow-soft";
  return (
    <div className="absolute bottom-4 left-4 flex flex-col gap-1.5 z-10">
      <button type="button" aria-label="Acercar" className={btn}
        onClick={() => camera.animatedZoom({ duration: 280 })}>
        <Plus size={16} />
      </button>
      <button type="button" aria-label="Alejar" className={btn}
        onClick={() => camera.animatedUnzoom({ duration: 280 })}>
        <Minus size={16} />
      </button>
      <button type="button" aria-label="Centrar" className={btn}
        onClick={() => camera.animatedReset({ duration: 320 })}>
        <Maximize2 size={15} />
      </button>
    </div>
  );
}

export function GraphView({
  snapshot,
  kindsFilter,
  ambient = false,
  selectedId,
  onSelectEntity,
}: GraphViewProps) {
  const signature = useMemo(
    () => `${snapshot.node_count}:${(kindsFilter ?? []).join(",")}`,
    [snapshot.node_count, kindsFilter],
  );

  const settings = useMemo(
    () => ({
      nodeProgramClasses: { image: NodeImageProgram, border: NodeBorderProgram },
      edgeProgramClasses: { curved: EdgeCurveProgram },
      defaultNodeType: "image",
      defaultEdgeType: "curved",
      renderLabels: !ambient,
      renderEdgeLabels: !ambient,
      labelFont: '"DM Sans", system-ui, sans-serif',
      labelSize: 13,
      labelWeight: "600",
      labelColor: { color: cssVar("--color-midnight-ink", "#0a0a0a") },
      edgeLabelFont: '"DM Sans", system-ui, sans-serif',
      edgeLabelSize: 11,
      edgeLabelColor: { color: cssVar("--color-muted-stone", "#6b7280") },
      // Declutter: fewer, larger label cells + a rendered-size floor so only
      // hubs label when zoomed out; everything labels as you zoom in.
      labelDensity: 0.55,
      labelGridCellSize: 150,
      labelRenderedSizeThreshold: ambient ? Number.POSITIVE_INFINITY : 7,
      defaultNodeColor: colorForArea("general"),
      zIndex: true,
      allowInvalidContainer: true,
      enableEdgeEvents: false,
    }),
    [ambient],
  );

  if (snapshot.node_count === 0 && !ambient) {
    return null; // empty state handled by the page
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
            <ClusterLabels signature={signature} />
            <GraphEvents selectedId={selectedId} onSelectEntity={onSelectEntity} />
            <ZoomControls />
          </>
        )}
      </SigmaContainer>
    </div>
  );
}
