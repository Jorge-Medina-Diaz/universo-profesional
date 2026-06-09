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
import { createNodeCompoundProgram } from "sigma/rendering";
import EdgeCurveProgram, { indexParallelEdgesIndex } from "@sigma/edge-curve";
import { Plus, Minus, Maximize2 } from "lucide-react";
import "@react-sigma/core/lib/style.css";
import type { GraphSnapshot } from "./api";
import { areaKey, colorForArea, colorForPillar, labelForArea } from "@/shared/areaColors";
import { iconFor, edgeLabel } from "./nodeIcons";
import { shapeFor } from "./nodeShapes";
import { kindColor } from "@/shared/kindColors";
import type { GraphAnimationCmd } from "./lensState";

// Program: coloured disc + white pictogram (area lens)
const CircleImageProgram = createNodeImageProgram({
  drawingMode: "background",
  keepWithinCircle: true,
  padding: 0.28,
});
const CircleCompound = createNodeCompoundProgram([CircleImageProgram, NodeBorderProgram]);

// Program: full shape + pictogram (kind-shapes lens)
const ShapeImageProgram = createNodeImageProgram({
  drawingMode: "background",
  keepWithinCircle: false,
  padding: 0.12,
});
const ShapeCompound = createNodeCompoundProgram([ShapeImageProgram, NodeBorderProgram]);

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

/** Convert #rrggbb or #rgb to rgba(r,g,b,a) for Sigma color attributes. */
function hexToRgba(hex: string, alpha: number): string {
  const h = hex.trim();
  let r = 0, g = 0, b = 0;
  if (h.length === 4 && h[0] === "#") {
    r = parseInt(h[1] + h[1], 16);
    g = parseInt(h[2] + h[2], 16);
    b = parseInt(h[3] + h[3], 16);
  } else if (h.length === 7 && h[0] === "#") {
    r = parseInt(h.slice(1, 3), 16);
    g = parseInt(h.slice(3, 5), 16);
    b = parseInt(h.slice(5, 7), 16);
  } else if (h.startsWith("rgb(")) {
    const m = h.match(/\d+/g);
    if (m) { r = parseInt(m[0]); g = parseInt(m[1]); b = parseInt(m[2]); }
  } else {
    return h;
  }
  return `rgba(${r}, ${g}, ${b}, ${alpha.toFixed(2)})`;
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
  sunbeam: string;
}
function readColors(): ThemeColors {
  return {
    ink: cssVar("--color-midnight-ink", "#0a0a0a"),
    stone: cssVar("--color-muted-stone", "#6b7280"),
    dim: cssVar("--hairline-strong", "rgba(10,10,10,0.12)"),
    leaf: cssVar("--color-leafy-green", "#6ece9d"),
    edge: cssVar("--hairline", "rgba(10,10,10,0.08)"),
    sunbeam: cssVar("--color-sunbeam-yellow", "#ffda6e"),
  };
}

export interface GraphSelection {
  id: string;
  kind: string;
  label: string;
}

/** What drives node grouping/colour/region-labels: semantic area or career pillar. */
export type GraphColorBy = "area" | "pillar";

export interface GraphViewProps {
  snapshot: GraphSnapshot;
  kindsFilter?: string[];
  /** Backdrop mode: no labels/interaction, dimmed. */
  ambient?: boolean;
  /** Controlled selection (highlights node + focuses camera). */
  selectedId?: string | null;
  /** Fired on node click / stage click (null). Parent opens the inspector. */
  onSelectEntity?: (sel: GraphSelection | null) => void;
  /** Group/colour the constellation by semantic area (default) or career pillar. */
  colorBy?: GraphColorBy;
  /** Search query — non-matching nodes dim to 20 %. */
  searchQuery?: string;
  /** Node IDs currently undergoing a discovery-celebration animation. */
  celebratingNodes?: Set<string>;
  /** Render nodes as per-kind coloured shapes instead of area-coloured circles. */
  shapeByKind?: boolean;
  /** Visually flag nodes that carry an ESCO ontology link. */
  showEsco?: boolean;
  /**
   * Local-graph mode: when set (and a node is selected), restrict the view to
   * the selected node's N-hop neighbourhood (BFS frontier). Undefined = off
   * (show the whole constellation). The biggest Obsidian "feels infinite but
   * stays navigable" win.
   */
  localDepth?: number;
  /** One-shot camera/highlight command from the agent (`animate_graph`). */
  animationCmd?: GraphAnimationCmd | null;
}

/** Resolve a node's group key, region label, and colour for the active lens. */
function resolveGroup(
  attrs: { area?: string | null; kind?: string; pillar?: string | null },
  colorBy: GraphColorBy,
): { key: string; label: string; color: string } {
  if (colorBy === "pillar") {
    const key = (attrs.pillar && attrs.pillar.trim()) || "Sin pilar";
    return { key, label: key, color: colorForPillar(key === "Sin pilar" ? null : key) };
  }
  const key = areaKey(attrs.area, attrs.kind);
  return { key, label: labelForArea(key), color: colorForArea(key) };
}

function GraphLoader({
  snapshot,
  kindsFilter,
  colorBy,
  shapeByKind,
  showEsco,
}: {
  snapshot: GraphSnapshot;
  kindsFilter?: string[];
  colorBy: GraphColorBy;
  shapeByKind?: boolean;
  showEsco?: boolean;
}) {
  const loadGraph = useLoadGraph();

  useEffect(() => {
    const g = new Graph({ multi: false, type: "directed" });
    const filtered = kindsFilter && kindsFilter.length > 0 ? new Set(kindsFilter) : null;

    const visible = snapshot.nodes.filter((n) => !filtered || filtered.has(n.attributes.kind));

    // Group into islands by the active lens (semantic area OR career pillar);
    // each group becomes a coherent, labelled, colour-coded island.
    const byGroup = new Map<string, typeof visible>();
    const groupMeta = new Map<string, { label: string; color: string }>();
    for (const n of visible) {
      const g0 = resolveGroup(n.attributes, colorBy);
      const list = byGroup.get(g0.key) ?? [];
      list.push(n);
      byGroup.set(g0.key, list);
      if (!groupMeta.has(g0.key)) groupMeta.set(g0.key, { label: g0.label, color: g0.color });
    }
    // Largest group is the core of the universe; the rest orbit it.
    const groups = Array.from(byGroup.keys()).sort(
      (a, b) => (byGroup.get(b)?.length ?? 0) - (byGroup.get(a)?.length ?? 0),
    );
    const islandRadius = (n: number) => 0.95 * Math.sqrt(Math.max(1, n));

    const placeIsland = (gkey: string, cx: number, cy: number) => {
      const meta = groupMeta.get(gkey) ?? { label: gkey, color: colorForArea("general") };
      const nodes = byGroup.get(gkey) ?? [];
      nodes.forEach((node, i) => {
        const a = i * 2.399963;
        const r = 0.95 * Math.sqrt(i);
        const jx = (seeded(node.key + "x") - 0.5) * 0.6;
        const jy = (seeded(node.key + "y") - 0.5) * 0.6;
        const kind = node.attributes.kind;
        const isEsco = showEsco && !!node.attributes.esco_uri;
        const nodeColor = shapeByKind ? kindColor(kind) : meta.color;

        g.addNode(node.key, {
          type: shapeByKind ? "shape" : "image",
          image: shapeByKind ? shapeFor(kind) : iconFor(kind),
          label: node.attributes.label,
          x: cx + Math.cos(a) * r + jx,
          y: cy + Math.sin(a) * r + jy,
          size: 16,
          color: nodeColor,
          kind,
          groupKey: gkey,
          groupLabel: meta.label,
          groupColor: meta.color,
          zIndex: 1,
          isEscoLinked: isEsco,
          escoUri: node.attributes.esco_uri ?? null,
          borderColor: isEsco ? "#f1c84b" : nodeColor,
          borderSize: isEsco ? 2.5 : 0,
        });
      });
    };

    const coreCount = byGroup.get(groups[0])?.length ?? 0;
    const satellites = groups.slice(1);
    const maxSatellite = Math.max(1, ...satellites.map((a) => byGroup.get(a)?.length ?? 0));
    const ring = islandRadius(coreCount) + islandRadius(maxSatellite) + 5.5;

    if (groups.length > 0) placeIsland(groups[0], 0, 0);
    satellites.forEach((gkey, si) => {
      const angle = (si / Math.max(1, satellites.length)) * Math.PI * 2 - Math.PI / 2;
      placeIsland(gkey, Math.cos(angle) * ring, Math.sin(angle) * ring);
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

    // Size by degree centrality — hubs read bigger.
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
  }, [loadGraph, snapshot, kindsFilter, colorBy, shapeByKind, showEsco]);

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

    const centroids = (): { key: string; label: string; color: string; x: number; y: number }[] => {
      const acc = new Map<
        string,
        { label: string; color: string; x: number; y: number; n: number }
      >();
      graph.forEachNode((_node, attr) => {
        const key = (attr.groupKey as string) ?? "";
        if (!key) return;
        const cur =
          acc.get(key) ?? {
            label: (attr.groupLabel as string) ?? key,
            color: (attr.groupColor as string) ?? "",
            x: 0,
            y: 0,
            n: 0,
          };
        cur.x += attr.x as number;
        cur.y += attr.y as number;
        cur.n += 1;
        acc.set(key, cur);
      });
      return Array.from(acc.entries())
        .filter(([, v]) => v.n > 0)
        .map(([key, v]) => ({ key, label: v.label, color: v.color, x: v.x / v.n, y: v.y / v.n }));
    };

    const update = () => {
      const seen = new Set<string>();
      for (const c of centroids()) {
        seen.add(c.key);
        let el = els.get(c.key);
        if (!el) {
          el = document.createElement("div");
          el.className = "cluster-label";
          el.textContent = c.label;
          el.style.setProperty("--cl-color", c.color);
          layer.appendChild(el);
          els.set(c.key, el);
        }
        const p = sigma.graphToViewport({ x: c.x, y: c.y });
        el.style.transform = `translate(-50%, -50%) translate(${p.x}px, ${p.y}px)`;
      }
      for (const [key, el] of els) {
        if (!seen.has(key)) {
          el.remove();
          els.delete(key);
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
  searchQuery,
  celebratingNodes,
  localDepth,
  animationCmd,
}: {
  selectedId?: string | null;
  onSelectEntity?: (sel: GraphSelection | null) => void;
  searchQuery?: string;
  celebratingNodes?: Set<string>;
  localDepth?: number;
  animationCmd?: GraphAnimationCmd | null;
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
  const celebrationStart = useRef<Map<string, number>>(new Map());
  // Local-graph BFS frontier (null = off). Read by the node/edge reducers.
  const frontier = useRef<Set<string> | null>(null);
  // Level-of-detail tier from the camera ratio. Read by the node reducer.
  const lodTier = useRef<"near" | "far">("near");

  // Merge prop celebrations into our animated timeline.
  useEffect(() => {
    const now = Date.now();
    for (const id of celebratingNodes ?? []) {
      if (!celebrationStart.current.has(id)) {
        celebrationStart.current.set(id, now);
      }
    }
  }, [celebratingNodes]);

  // Compute the local-graph frontier (BFS to `localDepth` hops from the selected
  // node) whenever the selection or depth changes. graphology's `neighbors()` is
  // direction-agnostic, so the neighbourhood spans in+out edges (what the user
  // expects). null = local mode off → the whole constellation shows.
  useEffect(() => {
    const graph = sigma.getGraph();
    if (!localDepth || !selectedId || !graph.hasNode(selectedId)) {
      frontier.current = null;
    } else {
      const seen = new Set<string>([selectedId]);
      let layer: string[] = [selectedId];
      for (let d = 0; d < localDepth; d++) {
        const next: string[] = [];
        for (const n of layer) {
          for (const nb of graph.neighbors(n)) {
            if (!seen.has(nb)) {
              seen.add(nb);
              next.push(nb);
            }
          }
        }
        layer = next;
      }
      frontier.current = seen;
    }
    sigma.refresh({ skipIndexation: true });
  }, [sigma, selectedId, localDepth]);

  // Level-of-detail: re-run the reducers when the camera crosses the far/near
  // zoom threshold, so a zoomed-out view collapses node art into coloured
  // regions (the DOM cluster labels still carry the names).
  useEffect(() => {
    const camera = sigma.getCamera();
    const onUpdate = () => {
      const tier = camera.ratio > 1.7 ? "far" : "near";
      if (tier !== lodTier.current) {
        lodTier.current = tier;
        sigma.refresh({ skipIndexation: true });
      }
    };
    camera.on("updated", onUpdate);
    return () => {
      camera.off("updated", onUpdate);
    };
  }, [sigma]);

  // Install reducers once; hover/selection/search/celebration flip refs + refresh.
  useEffect(() => {
    const graph = sigma.getGraph();

    sigma.setSetting("nodeReducer", (node, data) => {
      const res = { ...data } as Record<string, unknown>;
      // Local-graph mode: hide anything outside the selected node's N-hop
      // frontier so a dense universe stays navigable.
      if (frontier.current && !frontier.current.has(node)) {
        res.hidden = true;
        return res;
      }
      const now = Date.now();
      const celebrationStartTime = celebrationStart.current.get(node);
      const focus = hovered.current ?? selected.current;

      // Discovery celebration: spring scale + opacity + glow border.
      if (celebrationStartTime !== undefined) {
        const elapsed = now - celebrationStartTime;
        const progress = Math.min(elapsed / 800, 1);
        // Damped spring approx: 1 - e^(-6t)
        const springVal = 1 - Math.exp(-6 * progress);
        const baseSize = (data.size as number);
        res.size = baseSize * (0.2 + 0.8 * springVal);
        // Opacity via alpha on color
        const baseColor = String(data.color ?? colors.current.ink);
        res.color = hexToRgba(baseColor, springVal);
        // Glow border that fades over 2s
        const glowProgress = Math.min(elapsed / 2000, 1);
        res.borderColor = `rgba(255, 218, 110, ${1 - glowProgress})`;
        res.borderSize = 4 * (1 - glowProgress);
        res.zIndex = 3;
        if (elapsed > 2000) {
          celebrationStart.current.delete(node);
        }
      }

      // Search: matches PULSE with a glowing halo (Path-of-Exile style) and lift
      // slightly; non-matches dim so the eye lands on the matches. The pulse is
      // driven by the search rAF loop below (refreshes while a query is active).
      if (searchQuery && searchQuery.trim()) {
        const q = searchQuery.trim().toLowerCase();
        const label = String(data.label ?? "").toLowerCase();
        const matches = label.includes(q);
        if (!matches) {
          res.color = colors.current.dim;
          res.image = undefined;
          res.label = "";
          res.borderSize = 0;
        } else {
          const pulse = 0.5 + 0.5 * Math.sin((now / 1000) * Math.PI * 2);
          res.highlighted = true;
          res.borderColor = colors.current.sunbeam;
          res.borderSize = 3 + pulse * 4;
          res.size = (data.size as number) * (1.1 + pulse * 0.12);
          res.zIndex = 3;
        }
      }

      // Level-of-detail: zoomed far out with no active focus/search → drop the
      // pictogram + label so the map reads as coloured regions. Zoom in to
      // reveal nodes/edges/labels again.
      if (lodTier.current === "far" && !focus && !(searchQuery && searchQuery.trim())) {
        res.image = undefined;
        res.label = "";
      }

      // Hover / selection focus.
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
      // Local-graph mode: hide edges with an endpoint outside the frontier.
      if (frontier.current) {
        const [es, et] = graph.extremities(edge);
        if (!frontier.current.has(es) || !frontier.current.has(et)) {
          res.hidden = true;
          return res;
        }
      }
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
      mousemovebody: (e: CaptorCoords) => {
        if (!dragging.current || !dragged.current) return;
        const pos = sigma.viewportToGraph(e);
        graph.setNodeAttribute(dragged.current, "x", pos.x);
        graph.setNodeAttribute(dragged.current, "y", pos.y);
        dragMoved.current = true;
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
  }, [sigma, registerEvents, onSelectEntity, searchQuery]);

  // Animation loop for celebrations.
  useEffect(() => {
    let raf: number;
    const loop = () => {
      const now = Date.now();
      let hasActive = false;
      for (const [, start] of celebrationStart.current) {
        if (now - start < 2000) hasActive = true;
      }
      if (hasActive) {
        sigma.refresh({ skipIndexation: true });
        raf = requestAnimationFrame(loop);
      }
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [sigma]);

  // Animation loop for the search glow-pulse — runs ONLY while a query is
  // active, so matched-node halos breathe smoothly, then the loop stops.
  useEffect(() => {
    if (!searchQuery || !searchQuery.trim()) return;
    let raf: number;
    const loop = () => {
      sigma.refresh({ skipIndexation: true });
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [sigma, searchQuery]);

  // Agent-driven one-shot animations (animate_graph): cinematic camera flights
  // and node-set glows. Keyed on animationCmd.id so each command fires once and
  // an identical re-issue still plays. flyTo→camera.animate; pulse/highlightSet
  // reuse the celebration glow timeline; reset→camera.animatedReset.
  useEffect(() => {
    if (!animationCmd) return;
    const camera = sigma.getCamera();
    if (animationCmd.type === "reset") {
      camera.animatedReset({ duration: animationCmd.duration ?? 320 });
      return;
    }
    if (animationCmd.type === "flyTo") {
      const raf = requestAnimationFrame(() => {
        const d = sigma.getNodeDisplayData(animationCmd.entityId);
        if (d) {
          camera.animate(
            { x: d.x, y: d.y, ratio: animationCmd.zoom ?? Math.min(camera.ratio, 0.4) },
            { duration: animationCmd.duration ?? 600 },
          );
        }
      });
      return () => cancelAnimationFrame(raf);
    }
    // pulse / highlightSet → glow the ids via the celebration timeline + a local
    // rAF that refreshes until the glow window elapses.
    const start = Date.now();
    for (const id of animationCmd.ids) celebrationStart.current.set(id, start);
    const dur = animationCmd.duration ?? 2200;
    let raf = 0;
    const loop = () => {
      sigma.refresh({ skipIndexation: true });
      if (Date.now() - start < dur) raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [sigma, animationCmd]);

  // Live theme switch.
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
  colorBy = "area",
  searchQuery,
  celebratingNodes,
  shapeByKind,
  showEsco,
  localDepth,
  animationCmd,
}: GraphViewProps) {
  const signature = useMemo(
    () => `${snapshot.node_count}:${(kindsFilter ?? []).join(",")}:${colorBy}:${shapeByKind ?? false}`,
    [snapshot.node_count, kindsFilter, colorBy, shapeByKind],
  );

  const settings = useMemo(
    () => ({
      nodeProgramClasses: { image: CircleCompound, shape: ShapeCompound, border: NodeBorderProgram },
      edgeProgramClasses: { curved: EdgeCurveProgram },
      defaultNodeType: shapeByKind ? "shape" : "image",
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
      labelDensity: 0.55,
      labelGridCellSize: 150,
      labelRenderedSizeThreshold: ambient ? Number.POSITIVE_INFINITY : 7,
      defaultNodeColor: colorForArea("general"),
      zIndex: true,
      allowInvalidContainer: true,
      enableEdgeEvents: false,
    }),
    [ambient, shapeByKind],
  );

  if (snapshot.node_count === 0 && !ambient) {
    return null;
  }

  return (
    <div className="relative h-full w-full">
      <SigmaContainer
        style={{ height: "100%", width: "100%", background: "transparent" }}
        settings={settings}
        className={ambient ? "pointer-events-none opacity-70" : undefined}
        aria-label="Grafo interactivo de tu universo profesional. Usa los controles de zoom o tabula para navegar."
      >
        <GraphLoader
          snapshot={snapshot}
          kindsFilter={kindsFilter}
          colorBy={colorBy}
          shapeByKind={shapeByKind}
          showEsco={showEsco}
        />
        {!ambient && (
          <>
            <ClusterLabels signature={signature} />
            <GraphEvents
              selectedId={selectedId}
              onSelectEntity={onSelectEntity}
              searchQuery={searchQuery}
              celebratingNodes={celebratingNodes}
              localDepth={localDepth}
              animationCmd={animationCmd}
            />
            <ZoomControls />
          </>
        )}
      </SigmaContainer>
    </div>
  );
}
