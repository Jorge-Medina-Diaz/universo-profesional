/**
 * UniverseWorkspace — the interactive "workspace" mode of the universe surface
 * (route /universe). Graph/outline/trajectory lenses (agent-driven via
 * present_graph_view), a controls rail (SidebarContent), node inspector, and the
 * shared agent chat (AgentChatMount).
 *
 * Ported from the former UniversePage. The chat mount, loading skeleton and
 * sidebar are now shared modules (no longer duplicated with the home surface).
 */
import { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "motion/react";
import { Sparkles, X, Search, Menu, ChevronUp } from "lucide-react";
import { documents } from "@/shared/api";
import { useChatState, type FocusEntity } from "@/chat/state";
import { useGraphLensState } from "@/graph/lensState";
import { graphApi, type GraphSnapshot } from "@/graph/api";
import type { GraphSelection } from "@/graph/GraphView";
import { NodeDetailDrawer } from "@/graph/NodeDetailDrawer";
import { OutlineLens } from "./OutlineLens";
import { TrajectoryLens } from "./TrajectoryLens";
import { SidebarContent, type SidebarContentProps } from "./SidebarContent";
import { AREA_ORDER, areaKey, colorForArea, colorForPillar, labelForArea } from "@/shared/areaColors";
import { AgentChatMount } from "@/chat/AgentChatMount";
import { queryKeys } from "@/shared/queryKeys";
import { useDiscoveryStream } from "@/shared/hooks/useDiscoveryStream";
import { useEscapeKey } from "@/shared/useEscapeKey";
import { Button, GalaxyIllustration, Skeleton, toast } from "@/ui";

const GraphView = lazy(() =>
  import("@/graph/GraphView").then((m) => ({ default: m.GraphView })),
);

type Lens = "graph" | "outline" | "trajectory";

function readHashParams(): Record<string, string> {
  const hash = window.location.hash;
  const qIdx = hash.indexOf("?");
  if (qIdx === -1) return {};
  const params = new URLSearchParams(hash.slice(qIdx + 1));
  const out: Record<string, string> = {};
  for (const [k, v] of params) out[k] = v;
  return out;
}

function writeHashParams(params: Record<string, string | undefined>) {
  const base = "#/universe";
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "") as [string, string][];
  if (entries.length === 0) {
    window.location.hash = base;
    return;
  }
  const sp = new URLSearchParams(entries);
  window.location.hash = `${base}?${sp.toString()}`;
}

export function UniverseWorkspace() {
  const [lens, setLens] = useState<Lens>("graph");
  // Agent-addressable view knobs live in the shared control store (lensState.ts)
  // so the chat coordinator AND the sidebar write the same place — the agent can
  // filter / hide areas / switch lens / search / animate the constellation.
  const activeKinds = useGraphLensState((s) => s.activeKinds);
  const hiddenAreas = useGraphLensState((s) => s.hiddenAreas);
  const colorBy = useGraphLensState((s) => s.colorBy);
  const localGraph = useGraphLensState((s) => s.localGraph);
  const depth = useGraphLensState((s) => s.depth);
  const searchQuery = useGraphLensState((s) => s.search);
  const shapeByKind = useGraphLensState((s) => s.shapeByKind);
  const animationCmd = useGraphLensState((s) => s.animationCmd);
  const setView = useGraphLensState((s) => s.setView);
  const toggleKind = useGraphLensState((s) => s.toggleKind);
  const clearKinds = useGraphLensState((s) => s.clearKinds);
  const toggleArea = useGraphLensState((s) => s.toggleArea);
  const [selectedNode, setSelectedNode] = useState<GraphSelection | null>(null);
  const [enriching, setEnriching] = useState(false);
  const [celebratingNodes, setCelebratingNodes] = useState<Set<string>>(new Set());
  const [showEsco, setShowEsco] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const setFocus = useChatState((s) => s.setFocus);
  const queryClient = useQueryClient();
  const prevNodeIds = useRef<Set<string>>(new Set());
  const skipCelebrateRef = useRef(true);
  const restoredNodeRef = useRef(false);

  // Real-time discovery SSE stream.
  useDiscoveryStream(lens === "graph");

  // The lens is driven by the AGENT (present_graph_view → useGraphLensState):
  // there is no manual switcher — the user asks and the agent pivots.
  const lensMode = useGraphLensState((s) => s.mode);
  const lensRevision = useGraphLensState((s) => s.revision);
  const focusEntityId = useGraphLensState((s) => s.focusEntityId);
  useEffect(() => {
    if (lensRevision === 0) return;
    if (lensMode === "timeline") setLens("trajectory");
    else if (lensMode === "outline") setLens("outline");
    else setLens("graph");
  }, [lensMode, lensRevision]);

  // Parse URL hash params on mount → seed the control store.
  useEffect(() => {
    const params = readHashParams();
    if (params.types) setView({ activeKinds: new Set(params.types.split(",").filter(Boolean)) });
    if (params.search) setView({ search: params.search });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist state to URL hash.
  useEffect(() => {
    writeHashParams({
      types: activeKinds.size > 0 ? Array.from(activeKinds).join(",") : undefined,
      search: searchQuery.trim() || undefined,
      node: selectedNode?.id || undefined,
    });
  }, [activeKinds, searchQuery, selectedNode?.id]);

  const snapshotQuery = useQuery({
    queryKey: queryKeys.graph.snapshot,
    queryFn: () => graphApi.snapshot(false),
    staleTime: 30_000,
  });

  const pillarsQuery = useQuery({
    queryKey: queryKeys.graph.communities,
    queryFn: () => graphApi.communities(),
    staleTime: 60_000,
  });

  const documentsQuery = useQuery({
    queryKey: queryKeys.documents.all,
    queryFn: () => documents.list(),
    staleTime: 30_000,
  });

  // Documents are part of the universe: overlay them as `document` nodes.
  const baseSnapshot: GraphSnapshot | null = useMemo(() => {
    if (!snapshotQuery.data) return null;
    const docs = documentsQuery.data ?? [];
    if (docs.length === 0) return snapshotQuery.data;
    const nodeIds = new Set(snapshotQuery.data.nodes.map((n) => n.key));
    const docNodes = docs.map((d) => ({
      key: `doc-${d.id}`,
      attributes: {
        kind: "document",
        label: `${d.kind === "cover_letter" ? "Carta" : "CV"} · ${new Date(
          d.created_at,
        ).toLocaleDateString("es-ES", { day: "2-digit", month: "short" })}`,
      },
    }));
    const docEdges = docs.flatMap((d) =>
      (d.source_entity_ids ?? [])
        .filter((eid) => nodeIds.has(eid))
        .map((eid) => ({
          key: `doc-${d.id}-${eid}`,
          source: `doc-${d.id}`,
          target: eid,
          attributes: { edge_type: "generated_from" },
        })),
    );
    return {
      nodes: [...snapshotQuery.data.nodes, ...docNodes],
      edges: [...snapshotQuery.data.edges, ...docEdges],
      node_count: snapshotQuery.data.node_count + docNodes.length,
      edge_count: snapshotQuery.data.edge_count + docEdges.length,
    };
  }, [snapshotQuery.data, documentsQuery.data]);

  const kindCounts = useMemo(() => {
    if (!baseSnapshot) return new Map<string, number>();
    const counts = new Map<string, number>();
    for (const node of baseSnapshot.nodes) {
      counts.set(node.attributes.kind, (counts.get(node.attributes.kind) ?? 0) + 1);
    }
    return counts;
  }, [baseSnapshot]);

  // Restore selected node from URL once the snapshot is available.
  useEffect(() => {
    if (!baseSnapshot || restoredNodeRef.current) return;
    const params = readHashParams();
    if (params.node) {
      const node = baseSnapshot.nodes.find((n) => n.key === params.node);
      if (node) {
        setSelectedNode({ id: node.key, kind: node.attributes.kind, label: node.attributes.label });
      }
    }
    restoredNodeRef.current = true;
  }, [baseSnapshot]);

  // Detect newly added nodes and celebrate them.
  useEffect(() => {
    if (!baseSnapshot) return;
    const currentIds = new Set(baseSnapshot.nodes.map((n) => n.key));
    if (skipCelebrateRef.current) {
      skipCelebrateRef.current = false;
      prevNodeIds.current = currentIds;
      return;
    }
    const newIds = new Set([...currentIds].filter((id) => !prevNodeIds.current.has(id)));
    if (newIds.size > 0) {
      setCelebratingNodes((prev) => {
        const next = new Set(prev);
        for (const id of newIds) next.add(id);
        return next;
      });
      setTimeout(() => {
        setCelebratingNodes((prev) => {
          const next = new Set(prev);
          for (const id of newIds) next.delete(id);
          return next;
        });
      }, 3000);
    }
    prevNodeIds.current = currentIds;
  }, [baseSnapshot]);

  // Listen to discovery celebration events and refetch the snapshot.
  useEffect(() => {
    const handler = () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.graph.snapshot });
    };
    window.addEventListener("discovery:celebrate", handler);
    return () => window.removeEventListener("discovery:celebrate", handler);
  }, [queryClient]);

  const knownKinds = useMemo(() => {
    if (!baseSnapshot) return [] as string[];
    const set = new Set<string>();
    for (const node of baseSnapshot.nodes) set.add(node.attributes.kind);
    return Array.from(set).sort();
  }, [baseSnapshot]);

  // The group key a node belongs to under the active lens — used by both the
  // legend and its interactive show/hide toggles.
  const groupKeyOf = useCallback(
    (n: GraphSnapshot["nodes"][number]): string =>
      colorBy === "pillar"
        ? ((n.attributes.pillar as string | null) || "Sin pilar")
        : areaKey(n.attributes.area, n.attributes.kind),
    [colorBy],
  );

  const filteredSnapshot: GraphSnapshot | null = useMemo(() => {
    if (!baseSnapshot) return null;
    if (activeKinds.size === 0 && hiddenAreas.size === 0) return baseSnapshot;
    const visible = new Set<string>();
    const nodes = baseSnapshot.nodes.filter((n) => {
      if (activeKinds.size > 0 && !activeKinds.has(n.attributes.kind)) return false;
      if (hiddenAreas.size > 0 && hiddenAreas.has(groupKeyOf(n))) return false;
      visible.add(n.key);
      return true;
    });
    const edges = baseSnapshot.edges.filter((e) => visible.has(e.source) && visible.has(e.target));
    return { nodes, edges, node_count: nodes.length, edge_count: edges.length };
  }, [baseSnapshot, activeKinds, hiddenAreas, groupKeyOf]);

  // Chat → graph: focus an entity when the agent calls present_graph_view.
  useEffect(() => {
    if (lensRevision === 0 || !focusEntityId || !baseSnapshot) return;
    const node = baseSnapshot.nodes.find((n) => n.key === focusEntityId);
    if (node) {
      setSelectedNode({ id: node.key, kind: node.attributes.kind, label: node.attributes.label });
    }
  }, [focusEntityId, lensRevision, baseSnapshot]);

  // Legend is built from the BASE snapshot (kind-filtered, but NOT area-hidden)
  // so a hidden group still renders as a toggle-off chip you can switch back on.
  const legendSource = useMemo<GraphSnapshot | null>(() => {
    if (!baseSnapshot) return null;
    if (activeKinds.size === 0) return baseSnapshot;
    const nodes = baseSnapshot.nodes.filter((n) => activeKinds.has(n.attributes.kind));
    return { ...baseSnapshot, nodes, node_count: nodes.length };
  }, [baseSnapshot, activeKinds]);

  const legend = useMemo<{ key: string; label: string; color: string }[]>(() => {
    if (!legendSource) return [];
    if (colorBy === "pillar") {
      const seen = new Map<string, { key: string; label: string; color: string }>();
      for (const n of legendSource.nodes) {
        const p = (n.attributes.pillar as string | null) || null;
        const key = p || "Sin pilar";
        if (!seen.has(key)) seen.set(key, { key, label: key, color: colorForPillar(p) });
      }
      return [...seen.values()];
    }
    const set = new Set<string>();
    for (const n of legendSource.nodes) set.add(areaKey(n.attributes.area, n.attributes.kind));
    return AREA_ORDER.filter((a) => set.has(a)).map((a) => ({
      key: a,
      label: labelForArea(a),
      color: colorForArea(a),
    }));
  }, [legendSource, colorBy]);

  const handleFocus = (id: string, kind: string, label: string) => {
    if (kind === "document") {
      window.location.hash = `#/documents/${id.replace(/^doc-/, "")}`;
      return;
    }
    setFocus({ entity: kind as FocusEntity, id, meta: { label } });
    useChatState.getState().setPendingInjection({ content: `Hablemos sobre ${label}.` });
    useChatState.getState().setChatExpanded(true);
  };

  const handleEnrich = useCallback(async () => {
    if (enriching) return;
    setEnriching(true);
    try {
      await graphApi.enrich();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.graph.snapshot }),
        queryClient.invalidateQueries({ queryKey: queryKeys.graph.communities }),
      ]);
    } catch (e) {
      toast.error("No se pudieron inferir conexiones", (e as Error).message);
    } finally {
      setEnriching(false);
    }
  }, [enriching, queryClient]);

  // Auto-connect: a fresh import lands as isolated nodes (the semantic
  // RELATED_TO web is only inferred by enrichment). If we have a non-trivial
  // universe but zero edges, fire enrichment ONCE so the constellation shows
  // its relationships without the user hunting for the "Conectar" button.
  const autoEnrichedRef = useRef(false);
  useEffect(() => {
    const snap = snapshotQuery.data;
    if (!snap || enriching || autoEnrichedRef.current) return;
    if (snap.node_count > 3 && snap.edge_count === 0) {
      autoEnrichedRef.current = true;
      void handleEnrich();
    }
  }, [snapshotQuery.data, enriching, handleEnrich]);

  const isEmpty = !snapshotQuery.isLoading && (filteredSnapshot?.node_count ?? 0) === 0;

  // Local-graph mode only engages once a node is selected to anchor the BFS.
  const localDepth = localGraph && selectedNode ? depth : undefined;

  useEscapeKey(() => setMobileSidebarOpen(false), mobileSidebarOpen);

  // One prop bundle, spread into BOTH the desktop aside and the mobile sheet
  // (was a byte-identical duplicate).
  const sidebarProps: SidebarContentProps = {
    pillars: pillarsQuery.data?.items ?? null,
    knownKinds,
    kindCounts,
    activeKinds,
    onToggleKind: toggleKind,
    onClearKinds: clearKinds,
    colorBy,
    onSetColorBy: (v) => setView({ colorBy: v }),
    localGraph,
    onSetLocalGraph: (v) => setView({ localGraph: v }),
    depth,
    onSetDepth: (v) => setView({ depth: v }),
    hasSelection: !!selectedNode,
    shapeByKind,
    onSetShapeByKind: (v) => setView({ shapeByKind: v }),
    showEsco,
    onSetShowEsco: setShowEsco,
    legend,
    hiddenAreas,
    onToggleArea: toggleArea,
    filteredSnapshot,
    lens,
  };

  return (
    <div className="fixed inset-0 top-16 bottom-16 md:bottom-0 overflow-hidden constellation-bg flex">
      {/* ===== Left sidebar (desktop) ===== */}
      <aside className="z-20 hidden w-[300px] flex-shrink-0 flex-col gap-4 overflow-y-auto border-r border-hairline bg-canvas/50 p-4 backdrop-blur-sm md:flex">
        <SidebarContent {...sidebarProps} />
      </aside>

      {/* ===== Main content area ===== */}
      <div className="relative min-w-0 flex-1">
        {lens === "graph" && !isEmpty ? <div className="graph-nebula" aria-hidden /> : null}

        <div className="absolute inset-0">
          <AnimatePresence mode="wait">
            {snapshotQuery.isLoading ? (
              <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full">
                {lens === "graph" ? <GraphSkeleton /> : lens === "outline" ? <OutlineSkeleton /> : <TrajectorySkeleton />}
              </motion.div>
            ) : isEmpty ? (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full">
                <UniverseEmptyState />
              </motion.div>
            ) : lens === "graph" && filteredSnapshot ? (
              <motion.div key="graph" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full">
                <Suspense fallback={<GraphSkeleton />}>
                  <GraphView
                    snapshot={filteredSnapshot}
                    kindsFilter={Array.from(activeKinds)}
                    selectedId={selectedNode?.id ?? null}
                    onSelectEntity={setSelectedNode}
                    colorBy={colorBy}
                    searchQuery={searchQuery}
                    celebratingNodes={celebratingNodes}
                    shapeByKind={shapeByKind}
                    showEsco={showEsco}
                    localDepth={localDepth}
                    animationCmd={animationCmd}
                  />
                </Suspense>
              </motion.div>
            ) : lens === "outline" && filteredSnapshot ? (
              <motion.div key="outline" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full overflow-y-auto px-4 pb-32 pt-24">
                <div className="mx-auto max-w-3xl">
                  <OutlineLens snapshot={filteredSnapshot} onSelect={setSelectedNode} />
                </div>
              </motion.div>
            ) : (
              <motion.div key="trajectory" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full overflow-y-auto px-4 pb-32 pt-24">
                <div className="mx-auto max-w-3xl">
                  <TrajectoryLens onSelect={setSelectedNode} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ===== Top HUD ===== */}
        <div className="pointer-events-none absolute inset-x-0 top-3 z-20 flex items-start justify-between gap-3 px-3">
          <button
            type="button"
            onClick={() => setMobileSidebarOpen(true)}
            className="hud-chip pointer-events-auto md:hidden"
            aria-label="Abrir panel lateral"
          >
            <Menu size={15} />
            <span className="text-[13px]">Panel</span>
            {activeKinds.size > 0 && (
              <span className="ml-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-ink text-[10px] text-canvas">
                {activeKinds.size}
              </span>
            )}
          </button>

          <div className="hidden md:block" />

          {lens === "graph" && !isEmpty ? (
            <div className="pointer-events-auto mx-2 max-w-xs flex-1">
              <div className="relative">
                <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-stone" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setView({ search: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && filteredSnapshot && searchQuery.trim()) {
                      const q = searchQuery.trim().toLowerCase();
                      const match = filteredSnapshot.nodes.find((n) => n.attributes.label.toLowerCase().includes(q));
                      if (match) setSelectedNode({ id: match.key, kind: match.attributes.kind, label: match.attributes.label });
                    }
                  }}
                  placeholder="Buscar en el grafo…"
                  className="h-9 w-full rounded-full border border-hairline bg-canvas/80 pl-8 pr-8 text-sm text-ink backdrop-blur transition-colors placeholder:text-stone/70 focus:border-ink/30 focus:outline-none"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setView({ search: "" })}
                    className="pointer-events-auto absolute right-2.5 top-1/2 -translate-y-1/2 text-stone hover:text-ink"
                    aria-label="Limpiar búsqueda"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1" />
          )}

          <div className="pointer-events-auto flex items-center gap-2">
            {localDepth ? (
              <button
                type="button"
                onClick={() => setView({ localGraph: false })}
                className="hud-chip pointer-events-auto"
                aria-label="Salir del grafo local"
                title="Salir del grafo local"
              >
                <span className="text-[13px] leading-none">
                  Local · {depth} {depth === 1 ? "salto" : "saltos"}
                </span>
                <X size={13} />
              </button>
            ) : null}
            <button
              type="button"
              onClick={handleEnrich}
              disabled={enriching || isEmpty}
              className="hud-chip pointer-events-auto disabled:opacity-50"
              aria-label="Conectar universo (inferir relaciones)"
              title="Inferir relaciones entre tus entidades"
            >
              <Sparkles size={15} className={enriching ? "animate-pulse" : undefined} />
              <span className="hidden text-[14px] leading-none sm:inline">
                {enriching ? "Conectando…" : "Conectar"}
              </span>
            </button>
          </div>
        </div>

        {/* ===== Node detail drawer ===== */}
        <NodeDetailDrawer
          selection={selectedNode}
          snapshot={filteredSnapshot}
          onClose={() => setSelectedNode(null)}
          onNavigate={setSelectedNode}
          onChatFocus={handleFocus}
        />

        {/* ===== Shared agent chat ===== */}
        <AgentChatMount />
      </div>

      {/* ===== Mobile bottom sheet ===== */}
      <AnimatePresence>
        {mobileSidebarOpen && (
          <motion.div key="mobile-sheet" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 md:hidden">
            <div className="absolute inset-0 bg-ink/20 backdrop-blur-sm" onClick={() => setMobileSidebarOpen(false)} />
            <motion.div
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 28, stiffness: 320 }}
              className="absolute inset-x-0 bottom-0 max-h-[70vh] overflow-y-auto rounded-t-2xl border-t border-hairline bg-canvas shadow-float"
            >
              {/* Drag-handle affordance + sticky header */}
              <div className="sticky top-0 z-10 border-b border-hairline bg-canvas/80 backdrop-blur">
                <div className="flex justify-center pt-2">
                  <span aria-hidden className="h-1 w-9 rounded-full bg-hairline-strong" />
                </div>
                <div className="flex items-center justify-between px-4 pb-3 pt-2">
                  <span className="font-display text-sm text-ink">Panel del universo</span>
                  <button
                    type="button"
                    onClick={() => setMobileSidebarOpen(false)}
                    className="grid h-7 w-7 place-items-center rounded-full text-stone transition-colors hover:bg-surface hover:text-ink"
                    aria-label="Cerrar panel"
                  >
                    <ChevronUp size={18} />
                  </button>
                </div>
              </div>
              <div className="p-4">
                <SidebarContent {...sidebarProps} />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Empty state — elegant constellation placeholder
function UniverseEmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <GalaxyIllustration className="text-ink opacity-90" width={200} height={150} />
      <h3 className="mt-4 font-display text-heading leading-tight text-ink">
        Tu universo está esperando
      </h3>
      <p className="mt-2 max-w-sm text-sm leading-relaxed text-stone">
        Cada skill, proyecto y experiencia se conecta aquí como una constelación
        navegable. Empieza importando lo que ya tienes o cuéntaselo al chat.
      </p>
      <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
        <Button onClick={() => (window.location.hash = "#/connections")}>Importar mis cuentas</Button>
        <Button variant="outline" onClick={() => (window.location.hash = "#/")}>
          Empezar en el chat
        </Button>
      </div>
    </div>
  );
}

// Per-lens loading skeletons — each mirrors the geometry of its lens
function GraphSkeleton() {
  const dots = [
    { top: "20%", left: "30%", size: 40 },
    { top: "32%", left: "60%", size: 26 },
    { top: "47%", left: "44%", size: 56 },
    { top: "60%", left: "26%", size: 30 },
    { top: "54%", left: "70%", size: 34 },
    { top: "72%", left: "52%", size: 24 },
    { top: "38%", left: "18%", size: 26 },
    { top: "76%", left: "36%", size: 30 },
    { top: "26%", left: "80%", size: 22 },
    { top: "66%", left: "82%", size: 28 },
  ];
  const links = [
    ["30%", "20%", "44%", "47%"],
    ["60%", "32%", "44%", "47%"],
    ["44%", "47%", "26%", "60%"],
    ["44%", "47%", "70%", "54%"],
    ["52%", "72%", "70%", "54%"],
    ["18%", "38%", "30%", "20%"],
  ] as const;
  return (
    <div className="relative h-full w-full overflow-hidden">
      <svg className="absolute inset-0 h-full w-full" aria-hidden preserveAspectRatio="none">
        {links.map(([x1, y1, x2, y2], i) => (
          <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--hairline)" strokeWidth="1" />
        ))}
      </svg>
      {dots.map((d, i) => (
        <Skeleton key={i} shape="circle" className="absolute -translate-x-1/2 -translate-y-1/2" style={{ top: d.top, left: d.left, width: d.size, height: d.size }} />
      ))}
    </div>
  );
}

function OutlineSkeleton() {
  return (
    <div className="h-full space-y-7 overflow-hidden p-6 md:p-8">
      {[0, 1, 2].map((g) => (
        <div key={g} className="space-y-3">
          <div className="flex items-center gap-2">
            <Skeleton shape="circle" className="h-2.5 w-2.5" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="ml-auto h-5 w-6 rounded-full" />
          </div>
          <div className="ml-5 space-y-2">
            {Array.from({ length: 4 - g }).map((_, i) => (
              <Skeleton key={i} className="h-3.5" style={{ width: `${70 - i * 12}%` }} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function TrajectorySkeleton() {
  return (
    <div className="relative h-full overflow-hidden p-6 md:p-8">
      <div className="absolute left-[27px] top-8 bottom-8 w-px bg-hairline md:left-[39px]" />
      <div className="space-y-6">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex items-start gap-4">
            <Skeleton shape="circle" className="relative z-10 h-4 w-4 shrink-0" />
            <div className="flex-1 space-y-2 pt-0.5">
              <div className="flex items-center gap-3">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-3 w-16" />
              </div>
              <Skeleton className="h-3.5" style={{ width: `${80 - i * 9}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
