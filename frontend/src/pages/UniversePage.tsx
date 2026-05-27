/**
 * UniversePage — graph-first view of the user's professional knowledge.
 *
 * Sprint Q rewrite. The page used to surface entities as enumerated
 * sections (education, experience, projects, …). The new version
 * exposes three lenses over the same underlying graph:
 *
 *   • Graph     — sigma.js force-directed visualisation (default)
 *   • Outline   — Tana-style flat list grouped by kind (power-user view)
 *   • Trajectory — timeline of episodes + entities (Sprint R adds the
 *                  full temporal slider; we ship a basic chronological
 *                  list now so the lens is usable).
 *
 * The agentic chat remains the primary interaction channel. Clicking
 * a graph node calls `setChatFocus()` so the user can ask "tell me
 * more about this" and the coordinator routes the next message.
 */
import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "motion/react";
import {
  Network,
  ListTree,
  GitBranch,
  Sparkles,
  X,
  Search,
  Menu,
  ChevronUp,
} from "lucide-react";
import { universe, documents } from "@/shared/api";
import { useChatState, type FocusEntity } from "@/chat/state";
import { useGraphLensState } from "@/graph/lensState";
import { graphApi, type GraphSnapshot, type CareerPillar } from "@/graph/api";
import type { GraphSelection } from "@/graph/GraphView";
import { NodeDetailDrawer } from "@/graph/NodeDetailDrawer";
import { OutlineLens } from "./_universe/OutlineLens";
import { TrajectoryLens } from "./_universe/TrajectoryLens";
import { KIND_COLORS, KIND_LABELS, DEFAULT_KIND_COLOR } from "@/shared/kindColors";
import { AREA_ORDER, areaKey, colorForArea, colorForPillar, labelForArea } from "@/shared/areaColors";
import { FloatingChat } from "@/chat/FloatingChat";
import { enableCopilot, useCopilotReady } from "@/app/CopilotProvider";
import { SuggestionBar } from "@/widgets/SuggestionBar";
import { queryKeys } from "@/shared/queryKeys";
import { ProfileCompleteness } from "@/widgets/ProfileCompleteness";
import { DiscoveryProgress } from "@/widgets/DiscoveryProgress";
import { useDiscoveryStream } from "@/shared/hooks/useDiscoveryStream";
import { useEscapeKey } from "@/shared/useEscapeKey";
import {
  Button,
  Card,
  GalaxyIllustration,
  SectionLabel,
  Skeleton,
  Switch,
  cn,
} from "@/ui";

const GraphView = lazy(() =>
  import("@/graph/GraphView").then((m) => ({ default: m.GraphView })),
);

const CopilotSurface = lazy(() =>
  import("./_chat/CopilotSurface").then((m) => ({ default: m.CopilotSurface })),
);

const UNIVERSE_CHAT_INSTRUCTIONS = `Eres el compañero agéntico del usuario, sobre su universo profesional en formato grafo navegable.
Habla en español por defecto. Tu trabajo es ayudarle a EXPLORAR y MANTENER su universo.
- Cuando quiera ver o explorar algo (sus skills, proyectos, experiencias, un área como backend/IA/cloud, o cómo se conectan), usa \`universe_retrieve\` para encontrar los nodos y luego \`present_graph_view(mode, focus_entity_id?)\` para pilotar el grafo (focus | cluster | timeline | ontology_overlay). El grafo de esta página reaccionará: enfoca el nodo y abre su ficha.
- Coherencia primero: antes de crear algo nuevo, considera si es una actualización. Usa las propose_* tools (muestran cards) y nunca guardes sin confirmación.
- Una pregunta por turno.`;

const UNIVERSE_CHAT_INITIAL = `Este es tu universo. Pídeme que te enseñe un área ("muéstrame mi stack de backend"), que enfoque algo, o cuéntame algo nuevo para añadirlo.`;

type Lens = "graph" | "outline" | "trajectory";

const LENSES: { id: Lens; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "graph", label: "Universo", icon: Network },
  { id: "outline", label: "Outline", icon: ListTree },
  { id: "trajectory", label: "Trayectoria", icon: GitBranch },
];

// URL hash helpers

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

// Main component

export function UniversePage() {
  useEffect(() => {
    enableCopilot();
  }, []);

  const [lens, setLens] = useState<Lens>("graph");
  const [activeKinds, setActiveKinds] = useState<Set<string>>(new Set());
  const [selectedNode, setSelectedNode] = useState<GraphSelection | null>(null);
  const [, setChatExpanded] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [colorBy, setColorBy] = useState<"area" | "pillar">("area");
  const [searchQuery, setSearchQuery] = useState("");
  const [celebratingNodes, setCelebratingNodes] = useState<Set<string>>(new Set());
  const [shapeByKind, setShapeByKind] = useState(false);
  const [showEsco, setShowEsco] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const setFocus = useChatState((s) => s.setFocus);
  const chatReady = useCopilotReady();
  const queryClient = useQueryClient();
  const prevNodeIds = useRef<Set<string>>(new Set());
  const skipCelebrateRef = useRef(true);
  const restoredNodeRef = useRef(false);

  // Real-time discovery SSE stream.
  useDiscoveryStream(lens === "graph");

  // React to the agent's `present_graph_view` tool: map its modes onto
  // our three lenses so a chat turn can pivot the visualisation.
  const lensMode = useGraphLensState((s) => s.mode);
  const lensRevision = useGraphLensState((s) => s.revision);
  const focusEntityId = useGraphLensState((s) => s.focusEntityId);
  useEffect(() => {
    if (lensRevision === 0) return;
    setLens(lensMode === "timeline" ? "trajectory" : "graph");
  }, [lensMode, lensRevision]);

  // Parse URL hash params on mount.
  useEffect(() => {
    const params = readHashParams();
    if (params.types) {
      setActiveKinds(new Set(params.types.split(",").filter(Boolean)));
    }
    if (params.search) {
      setSearchQuery(params.search);
    }
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

  const summaryQuery = useQuery({
    queryKey: queryKeys.universe.summary,
    queryFn: universe.summary,
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

  // Documents are part of the universe: overlay them as `document` nodes with
  // `generated_from` edges to the entities they were built from.
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

  // Count nodes per kind for the filter chips.
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
        setSelectedNode({
          id: node.key,
          kind: node.attributes.kind,
          label: node.attributes.label,
        });
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

  // Listen to discovery celebration events and trigger a snapshot refetch
  // so the diff effect above can pick up new nodes quickly.
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
    for (const node of baseSnapshot.nodes) {
      set.add(node.attributes.kind);
    }
    return Array.from(set).sort();
  }, [baseSnapshot]);

  const filteredSnapshot: GraphSnapshot | null = useMemo(() => {
    if (!baseSnapshot) return null;
    if (activeKinds.size === 0) return baseSnapshot;
    const visible = new Set<string>();
    const nodes = baseSnapshot.nodes.filter((n) => {
      if (activeKinds.has(n.attributes.kind)) {
        visible.add(n.key);
        return true;
      }
      return false;
    });
    const edges = baseSnapshot.edges.filter(
      (e) => visible.has(e.source) && visible.has(e.target),
    );
    return {
      nodes,
      edges,
      node_count: nodes.length,
      edge_count: edges.length,
    };
  }, [baseSnapshot, activeKinds]);

  // Chat → graph: when the agent focuses an entity via `present_graph_view`,
  // select that node here so the camera animates to it and the inspector opens.
  useEffect(() => {
    if (lensRevision === 0 || !focusEntityId || !baseSnapshot) return;
    const node = baseSnapshot.nodes.find((n) => n.key === focusEntityId);
    if (node) {
      setSelectedNode({
        id: node.key,
        kind: node.attributes.kind,
        label: node.attributes.label,
      });
    }
  }, [focusEntityId, lensRevision, baseSnapshot]);

  // Legend reflects the active lens: semantic areas or career pillars.
  const legend = useMemo<{ key: string; label: string; color: string }[]>(() => {
    if (!filteredSnapshot) return [];
    if (colorBy === "pillar") {
      const seen = new Map<string, { key: string; label: string; color: string }>();
      for (const n of filteredSnapshot.nodes) {
        const p = (n.attributes.pillar as string | null) || null;
        const key = p || "Sin pilar";
        if (!seen.has(key)) seen.set(key, { key, label: key, color: colorForPillar(p) });
      }
      return [...seen.values()];
    }
    const set = new Set<string>();
    for (const n of filteredSnapshot.nodes) {
      set.add(areaKey(n.attributes.area, n.attributes.kind));
    }
    return AREA_ORDER.filter((a) => set.has(a)).map((a) => ({
      key: a,
      label: labelForArea(a),
      color: colorForArea(a),
    }));
  }, [filteredSnapshot, colorBy]);

  const handleFocus = (id: string, kind: string, label: string) => {
    if (kind === "document") {
      window.location.hash = `#/documents/${id.replace(/^doc-/, "")}`;
      return;
    }
    setFocus({
      entity: kind as FocusEntity,
      id,
      meta: { label },
    });
    useChatState.getState().setPendingInjection({ content: `Hablemos sobre ${label}.` });
    useChatState.getState().setChatExpanded(true);
  };

  const handleEnrich = async () => {
    if (enriching) return;
    setEnriching(true);
    try {
      await graphApi.enrich();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.graph.snapshot }),
        queryClient.invalidateQueries({ queryKey: queryKeys.graph.communities }),
      ]);
    } finally {
      setEnriching(false);
    }
  };

  const isEmpty = !snapshotQuery.isLoading && (filteredSnapshot?.node_count ?? 0) === 0;

  // Close mobile sidebar on Escape.
  useEscapeKey(() => setMobileSidebarOpen(false), mobileSidebarOpen);

  return (
    <div className="fixed inset-0 top-16 bottom-16 md:bottom-0 overflow-hidden constellation-bg flex">
      {/* ===== Left sidebar (desktop) ===== */}
      <aside className="hidden md:flex w-[280px] flex-shrink-0 flex-col gap-3 p-3 overflow-y-auto border-r border-hairline bg-canvas/50 backdrop-blur-sm z-20">
        <SidebarContent
          summaryCounts={summaryQuery.data?.counts ?? null}
          pillars={pillarsQuery.data?.items ?? null}
          knownKinds={knownKinds}
          kindCounts={kindCounts}
          activeKinds={activeKinds}
          onToggleKind={(k) => {
            setActiveKinds((prev) => {
              const next = new Set(prev);
              if (next.has(k)) next.delete(k);
              else next.add(k);
              return next;
            });
          }}
          onClearKinds={() => setActiveKinds(new Set())}
          colorBy={colorBy}
          onSetColorBy={setColorBy}
          shapeByKind={shapeByKind}
          onSetShapeByKind={setShapeByKind}
          showEsco={showEsco}
          onSetShowEsco={setShowEsco}
          legend={legend}
          filteredSnapshot={filteredSnapshot}
          lens={lens}
        />
      </aside>

      {/* ===== Main content area ===== */}
      <div className="flex-1 relative min-w-0">
        {/* Cosmic backdrop (graph lens only) */}
        {lens === "graph" && !isEmpty ? <div className="graph-nebula" aria-hidden /> : null}

        {/* Lens surface */}
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
                  />
                </Suspense>
              </motion.div>
            ) : lens === "outline" && filteredSnapshot ? (
              <motion.div
                key="outline"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-full overflow-y-auto px-4 pb-32 pt-24"
              >
                <div className="mx-auto max-w-3xl">
                  <OutlineLens snapshot={filteredSnapshot} onSelect={setSelectedNode} />
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="trajectory"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-full overflow-y-auto px-4 pb-32 pt-24"
              >
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
              <span className="ml-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-ink text-canvas text-[10px]">
                {activeKinds.size}
              </span>
            )}
          </button>

          <div className="hidden md:block" />

          {/* Search */}
          {lens === "graph" && !isEmpty ? (
            <div className="pointer-events-auto flex-1 max-w-xs mx-2">
              <div className="relative">
                <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-stone pointer-events-none" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && filteredSnapshot && searchQuery.trim()) {
                      const q = searchQuery.trim().toLowerCase();
                      const match = filteredSnapshot.nodes.find((n) =>
                        n.attributes.label.toLowerCase().includes(q),
                      );
                      if (match) {
                        setSelectedNode({ id: match.key, kind: match.attributes.kind, label: match.attributes.label });
                      }
                    }
                  }}
                  placeholder="Buscar en el grafo…"
                  className="w-full h-9 pl-8 pr-8 rounded-full bg-canvas/80 backdrop-blur border border-hairline text-sm text-ink placeholder:text-stone/70 focus:outline-none focus:border-ink/30 transition-colors"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery("")}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-stone hover:text-ink pointer-events-auto"
                    aria-label="Limpiar búsqueda"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            </div>
          ) : <div className="flex-1" />}

          <div className="pointer-events-auto flex items-center gap-2">
            <LensSwitcher current={lens} onChange={setLens} />
            <button
              type="button"
              onClick={handleEnrich}
              disabled={enriching || isEmpty}
              className="hud-chip pointer-events-auto disabled:opacity-50"
              aria-label="Conectar universo (inferir relaciones)"
              title="Inferir relaciones entre tus entidades"
            >
              <Sparkles size={15} className={enriching ? "animate-pulse" : undefined} />
              <span className="hidden sm:inline text-[14px] leading-none">
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

        {/* ===== Floating chat ===== */}
        <FloatingChat onExpandedChange={setChatExpanded}>
          {chatReady ? (
            <Suspense fallback={<ChatLoadingSkeleton />}>
              <CopilotSurface
                instructions={UNIVERSE_CHAT_INSTRUCTIONS}
                title="Tu universo · chat"
                initial={UNIVERSE_CHAT_INITIAL}
              />
            </Suspense>
          ) : (
            <ChatLoadingSkeleton />
          )}
        </FloatingChat>
      </div>

      {/* ===== Mobile bottom sheet ===== */}
      <AnimatePresence>
        {mobileSidebarOpen && (
          <motion.div
            key="mobile-sheet"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="md:hidden fixed inset-0 z-50"
          >
            <div
              className="absolute inset-0 bg-ink/20 backdrop-blur-sm"
              onClick={() => setMobileSidebarOpen(false)}
            />
            <motion.div
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="absolute bottom-0 inset-x-0 max-h-[85vh] overflow-y-auto rounded-t-2xl bg-canvas border-t border-hairline shadow-float"
            >
              <div className="sticky top-0 z-10 flex items-center justify-between px-4 py-3 bg-canvas/80 backdrop-blur border-b border-hairline">
                <span className="font-display text-sm text-ink">Panel del universo</span>
                <button
                  type="button"
                  onClick={() => setMobileSidebarOpen(false)}
                  className="grid h-7 w-7 place-items-center rounded-full text-stone hover:bg-surface hover:text-ink transition-colors"
                  aria-label="Cerrar panel"
                >
                  <ChevronUp size={18} />
                </button>
              </div>
              <div className="p-4 space-y-4">
                <SidebarContent
                  summaryCounts={summaryQuery.data?.counts ?? null}
                  pillars={pillarsQuery.data?.items ?? null}
                  knownKinds={knownKinds}
                  kindCounts={kindCounts}
                  activeKinds={activeKinds}
                  onToggleKind={(k) => {
                    setActiveKinds((prev) => {
                      const next = new Set(prev);
                      if (next.has(k)) next.delete(k);
                      else next.add(k);
                      return next;
                    });
                  }}
                  onClearKinds={() => setActiveKinds(new Set())}
                  colorBy={colorBy}
                  onSetColorBy={setColorBy}
                  shapeByKind={shapeByKind}
                  onSetShapeByKind={setShapeByKind}
                  showEsco={showEsco}
                  onSetShowEsco={setShowEsco}
                  legend={legend}
                  filteredSnapshot={filteredSnapshot}
                  lens={lens}
                />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Sidebar content — shared between desktop sidebar and mobile bottom sheet

interface SidebarContentProps {
  summaryCounts: Record<string, number> | null;
  pillars: CareerPillar[] | null;
  knownKinds: string[];
  kindCounts: Map<string, number>;
  activeKinds: Set<string>;
  onToggleKind: (k: string) => void;
  onClearKinds: () => void;
  colorBy: "area" | "pillar";
  onSetColorBy: (v: "area" | "pillar") => void;
  shapeByKind: boolean;
  onSetShapeByKind: (v: boolean) => void;
  showEsco: boolean;
  onSetShowEsco: (v: boolean) => void;
  legend: { key: string; label: string; color: string }[];
  filteredSnapshot: GraphSnapshot | null;
  lens: Lens;
}

function SidebarContent({
  summaryCounts,
  pillars,
  knownKinds,
  kindCounts,
  activeKinds,
  onToggleKind,
  onClearKinds,
  colorBy,
  onSetColorBy,
  shapeByKind,
  onSetShapeByKind,
  showEsco,
  onSetShowEsco,
  legend,
  filteredSnapshot,
  lens,
}: SidebarContentProps) {
  return (
    <div className="flex flex-col gap-3">
      <DiscoveryProgress />

      {/* Filters */}
      <div className="rounded-card border border-hairline bg-surface p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-ink">Filtrar por tipo</span>
          {activeKinds.size > 0 && (
            <button
              type="button"
              onClick={onClearKinds}
              className="text-[11px] text-stone hover:text-ink transition-colors"
            >
              Limpiar
            </button>
          )}
        </div>
        <KindFilters
          kinds={knownKinds}
          counts={kindCounts}
          active={activeKinds}
          onToggle={onToggleKind}
          onClear={onClearKinds}
        />
      </div>

      {/* Graph toggles */}
      {lens === "graph" && (
        <div className="rounded-card border border-hairline bg-surface p-3 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-ink/80">Mostrar vínculos ESCO</span>
            <Switch checked={showEsco} onChange={onSetShowEsco} />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-ink/80">Colorear por tipo</span>
            <Switch checked={shapeByKind} onChange={onSetShapeByKind} />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-ink/80">Colorear por</span>
            <div className="flex items-center gap-1 rounded-full border border-hairline bg-canvas/60 p-0.5 text-[11px]">
              <button
                type="button"
                onClick={() => onSetColorBy("area")}
                className={cn(
                  "rounded-full px-2 py-0.5 transition-colors",
                  colorBy === "area" ? "bg-ink text-canvas" : "text-stone hover:text-ink",
                )}
              >
                Áreas
              </button>
              <button
                type="button"
                onClick={() => onSetColorBy("pillar")}
                className={cn(
                  "rounded-full px-2 py-0.5 transition-colors",
                  colorBy === "pillar" ? "bg-ink text-canvas" : "text-stone hover:text-ink",
                )}
              >
                Pilares
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Legend */}
      {lens === "graph" && legend.length > 0 && filteredSnapshot && (
        <div className="rounded-card border border-hairline bg-surface p-3">
          <span className="text-xs font-medium text-stone mb-2 block">Leyenda</span>
          <div className="flex flex-wrap gap-x-3 gap-y-1.5">
            {legend.map((g) => (
              <span key={g.key} className="inline-flex items-center gap-1.5 text-[11px] text-ink/80">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: g.color }} />
                {g.label}
              </span>
            ))}
          </div>
          <p className="border-t border-hairline pt-1.5 mt-1.5 text-[11px] text-stone">
            {filteredSnapshot.node_count} nodos · {filteredSnapshot.edge_count} aristas
          </p>
        </div>
      )}

      {/* Summary */}
      {summaryCounts ? (
        <Card padding="lg" className="flex flex-col">
          <SectionLabel index={1} tone="leaf">Resumen</SectionLabel>
          <ul className="mt-4 space-y-2.5 text-sm">
            {Object.entries(summaryCounts).map(([k, v]) => (
              <li key={k} className="flex items-center justify-between border-b border-hairline pb-2 last:border-0 last:pb-0">
                <span className="flex items-center gap-2 text-stone">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: KIND_COLORS[k] ?? "#94a3b8" }} />
                  {KIND_LABELS[k] ?? k}
                </span>
                <span className="font-display text-[18px] tabular-nums text-ink">{v as number}</span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <ProfileCompleteness />
      <SuggestionBar />

      {pillars && pillars.length > 0 && (
        <Card padding="lg" className="flex flex-col">
          <SectionLabel index={1} tone="leaf">Pilares de carrera</SectionLabel>
          <ul className="mt-4 space-y-3">
            {pillars.map((p) => (
              <li key={p.id} className="border-b border-hairline pb-3 last:border-0 last:pb-0">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-display text-[15px] text-ink">{p.label}</span>
                  <span className="text-[11px] tabular-nums text-stone">{p.size}</span>
                </div>
                <p className="mt-1 text-xs leading-snug text-stone">{p.summary}</p>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

// Kind filters with per-type counts

function KindFilters({
  kinds,
  counts,
  active,
  onToggle,
  onClear,
}: {
  kinds: string[];
  counts: Map<string, number>;
  active: Set<string>;
  onToggle: (k: string) => void;
  onClear: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {kinds.map((k) => {
        const isActive = active.has(k);
        const color = KIND_COLORS[k] ?? DEFAULT_KIND_COLOR;
        const count = counts.get(k) ?? 0;
        return (
          <button
            key={k}
            type="button"
            onClick={() => onToggle(k)}
            aria-pressed={isActive}
            className={cn(
              "inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/20 focus-visible:ring-offset-1",
              isActive
                ? "border-ink/20 bg-ink/[0.04] text-ink"
                : "border-transparent text-ink/60 hover:text-ink",
            )}
          >
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
            {KIND_LABELS[k] ?? k}
            <span className={cn("text-[10px] tabular-nums", isActive ? "text-ink/70" : "text-stone/60")}>
              {count}
            </span>
          </button>
        );
      })}
      {active.size > 0 ? (
        <Button size="sm" variant="ghost" onClick={onClear} className="ml-1">
          Limpiar
        </Button>
      ) : null}
    </div>
  );
}

// Lens switcher

function LensSwitcher({
  current,
  onChange,
}: {
  current: Lens;
  onChange: (l: Lens) => void;
}) {
  return (
    <div className="inline-flex rounded-full border border-hairline bg-canvas p-1 text-sm">
      {LENSES.map(({ id, label, icon: Icon }) => {
        const isActive = current === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => onChange(id)}
            aria-pressed={isActive}
            className={cn(
              "flex items-center gap-1.5 px-3.5 py-1.5 rounded-full transition-colors duration-180 ease-pirsch focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/20 focus-visible:ring-offset-1",
              isActive
                ? "bg-ink text-canvas"
                : "text-stone hover:text-ink",
            )}
          >
            <Icon className="w-3.5 h-3.5" />
            <span>{label}</span>
          </button>
        );
      })}
    </div>
  );
}

// Empty state — elegant constellation placeholder

function UniverseEmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center px-6">
      <GalaxyIllustration className="opacity-90" width={200} height={150} />
      <h3 className="mt-4 font-display text-[26px] leading-tight text-ink">
        Tu universo está esperando
      </h3>
      <p className="mt-2 max-w-sm text-sm text-stone leading-relaxed">
        Cada skill, proyecto y experiencia se conecta aquí como una constelación
        navegable. Empieza importando lo que ya tienes o cuéntaselo al chat.
      </p>
      <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
        <Button onClick={() => (window.location.hash = "#/connections")}>
          Importar mis cuentas
        </Button>
        <Button variant="outline" onClick={() => (window.location.hash = "#/")}>
          Empezar en el chat
        </Button>
      </div>
    </div>
  );
}

// Per-lens loading skeletons — each mirrors the geometry of its lens

/** Grafo — scattered constellation of haloed dots with faint links. */
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
          <line
            key={i}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke="var(--hairline)"
            strokeWidth="1"
          />
        ))}
      </svg>
      {dots.map((d, i) => (
        <Skeleton
          key={i}
          shape="circle"
          className="absolute -translate-x-1/2 -translate-y-1/2"
          style={{ top: d.top, left: d.left, width: d.size, height: d.size }}
        />
      ))}
    </div>
  );
}

/** Outline — grouped list: section headers + indented item rows. */
function OutlineSkeleton() {
  return (
    <div className="h-full overflow-hidden p-6 md:p-8 space-y-7">
      {[0, 1, 2].map((g) => (
        <div key={g} className="space-y-3">
          <div className="flex items-center gap-2">
            <Skeleton shape="circle" className="h-2.5 w-2.5" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="ml-auto h-5 w-6 rounded-full" />
          </div>
          <div className="ml-5 space-y-2">
            {Array.from({ length: 4 - g }).map((_, i) => (
              <Skeleton
                key={i}
                className="h-3.5"
                style={{ width: `${70 - i * 12}%` }}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

/** Trayectoria — vertical timeline spine with nodes + content bars. */
function TrajectorySkeleton() {
  return (
    <div className="relative h-full overflow-hidden p-6 md:p-8">
      <div className="absolute left-[27px] md:left-[39px] top-8 bottom-8 w-px bg-hairline" />
      <div className="space-y-6">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex items-start gap-4">
            <Skeleton shape="circle" className="h-4 w-4 shrink-0 relative z-10" />
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

function ChatLoadingSkeleton() {
  return (
    <div className="flex h-full w-full max-w-[680px] mx-auto flex-col justify-end gap-4 p-4">
      <div className="flex gap-3 animate-pulse">
        <div className="w-7 h-7 rounded-full bg-black/10 shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-3 rounded bg-black/10 w-3/4" />
          <div className="h-3 rounded bg-black/10 w-1/2" />
        </div>
      </div>
      <div className="flex gap-3 justify-end animate-pulse">
        <div className="flex-1 space-y-2 max-w-[70%]">
          <div className="h-3 rounded bg-black/10 w-full" />
          <div className="h-3 rounded bg-black/10 w-2/3" />
        </div>
        <div className="w-7 h-7 rounded-full bg-black/10 shrink-0" />
      </div>
      <div className="flex gap-3 animate-pulse">
        <div className="w-7 h-7 rounded-full bg-black/10 shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-3 rounded bg-black/10 w-5/6" />
          <div className="h-3 rounded bg-black/10 w-4/5" />
          <div className="h-3 rounded bg-black/10 w-1/3" />
        </div>
      </div>
      <div className="mt-2 h-10 rounded-xl bg-black/8" />
    </div>
  );
}
