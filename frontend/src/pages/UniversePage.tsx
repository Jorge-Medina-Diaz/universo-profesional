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
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "motion/react";
import {
  Network,
  ListTree,
  GitBranch,
} from "lucide-react";
import { universe } from "@/shared/api";
import { useChatState, type FocusEntity } from "@/chat/state";
import { useGraphLensState } from "@/graph/lensState";
import { graphApi, type GraphSnapshot } from "@/graph/api";
import { GraphView } from "@/graph/GraphView";
import { KIND_COLORS, KIND_LABELS } from "@/shared/kindColors";
import { SuggestionBar } from "@/widgets/SuggestionBar";
import { ProfileCompleteness } from "@/widgets/ProfileCompleteness";
import {
  Badge,
  Button,
  Card,
  GalaxyIllustration,
  PageHeader,
  SectionLabel,
  Skeleton,
  cn,
} from "@/ui";

type Lens = "graph" | "outline" | "trajectory";

const LENSES: { id: Lens; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "graph", label: "Grafo", icon: Network },
  { id: "outline", label: "Outline", icon: ListTree },
  { id: "trajectory", label: "Trayectoria", icon: GitBranch },
];

export function UniversePage() {
  const [lens, setLens] = useState<Lens>("graph");
  const [activeKinds, setActiveKinds] = useState<Set<string>>(new Set());
  const setFocus = useChatState((s) => s.setFocus);

  // React to the agent's `present_graph_view` tool: map its modes onto
  // our three lenses so a chat turn can pivot the visualisation.
  const lensMode = useGraphLensState((s) => s.mode);
  const lensRevision = useGraphLensState((s) => s.revision);
  useEffect(() => {
    if (lensRevision === 0) return; // initial state, user hasn't been steered
    setLens(lensMode === "timeline" ? "trajectory" : "graph");
  }, [lensMode, lensRevision]);

  const snapshotQuery = useQuery({
    queryKey: ["graph", "snapshot"],
    queryFn: () => graphApi.snapshot(false),
    // Fresh enough — the graph dual-write hook invalidates this query
    // via the React Query cache key after coherence upserts.
    staleTime: 30_000,
  });

  const summaryQuery = useQuery({
    queryKey: ["universe", "summary"],
    queryFn: universe.summary,
  });

  const knownKinds = useMemo(() => {
    if (!snapshotQuery.data) return [] as string[];
    const set = new Set<string>();
    for (const node of snapshotQuery.data.nodes) {
      set.add(node.attributes.kind);
    }
    return Array.from(set).sort();
  }, [snapshotQuery.data]);

  const filteredSnapshot: GraphSnapshot | null = useMemo(() => {
    if (!snapshotQuery.data) return null;
    if (activeKinds.size === 0) return snapshotQuery.data;
    const visible = new Set<string>();
    const nodes = snapshotQuery.data.nodes.filter((n) => {
      if (activeKinds.has(n.attributes.kind)) {
        visible.add(n.key);
        return true;
      }
      return false;
    });
    const edges = snapshotQuery.data.edges.filter(
      (e) => visible.has(e.source) && visible.has(e.target),
    );
    return {
      nodes,
      edges,
      node_count: nodes.length,
      edge_count: edges.length,
    };
  }, [snapshotQuery.data, activeKinds]);

  const handleFocus = (id: string, kind: string, label: string) => {
    setFocus({
      entity: kind as FocusEntity,
      id,
      meta: { label },
    });
  };

  const isEmpty = !snapshotQuery.isLoading && (filteredSnapshot?.node_count ?? 0) === 0;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 lg:px-8 lg:py-10">
      <PageHeader
        eyebrow="Tu mapa profesional"
        title="Tu universo"
        subtitle="Skills, proyectos, experiencias y decisiones — todo conectado como un grafo navegable."
      />

      {/* Toolbar: lens switcher + legend */}
      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <LensSwitcher current={lens} onChange={setLens} />
        {knownKinds.length > 0 ? (
          <KindFilters
            kinds={knownKinds}
            active={activeKinds}
            onToggle={(k) => {
              setActiveKinds((prev) => {
                const next = new Set(prev);
                if (next.has(k)) next.delete(k);
                else next.add(k);
                return next;
              });
            }}
            onClear={() => setActiveKinds(new Set())}
          />
        ) : null}
      </div>

      {/* Hero graph */}
      <div className="mt-4 relative overflow-hidden rounded-card border border-hairline constellation-bg">
        <div className="relative h-[64vh] min-h-[460px]">
          <AnimatePresence mode="wait">
            {snapshotQuery.isLoading ? (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex h-full items-center justify-center"
              >
                <Skeleton className="h-64 w-64 rounded-full" />
              </motion.div>
            ) : isEmpty ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-full"
              >
                <UniverseEmptyState />
              </motion.div>
            ) : lens === "graph" && filteredSnapshot ? (
              <motion.div
                key="graph"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-full"
              >
                <GraphView snapshot={filteredSnapshot} onFocusEntity={handleFocus} />
              </motion.div>
            ) : lens === "outline" && filteredSnapshot ? (
              <motion.div
                key="outline"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-full overflow-y-auto p-6 md:p-8"
              >
                <OutlineLens snapshot={filteredSnapshot} onFocusEntity={handleFocus} />
              </motion.div>
            ) : (
              <motion.div
                key="trajectory"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-full overflow-y-auto p-6 md:p-8"
              >
                <TrajectoryLens snapshot={filteredSnapshot} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {filteredSnapshot && !isEmpty ? (
        <p className="mt-3 px-1 text-xs text-stone">
          {filteredSnapshot.node_count} nodos · {filteredSnapshot.edge_count} aristas
          {activeKinds.size > 0
            ? ` · filtrado: ${Array.from(activeKinds).map((k) => KIND_LABELS[k] ?? k).join(", ")}`
            : ""}
        </p>
      ) : null}

      {/* Insight cards — full width below the hero so text never gets cramped */}
      <div className="mt-8 grid gap-4 lg:grid-cols-3">
        <ProfileCompleteness />
        <SuggestionBar />
        {summaryQuery.data ? (
          <Card padding="lg" className="flex flex-col">
            <SectionLabel index={3} tone="leaf">
              Resumen
            </SectionLabel>
            <ul className="mt-4 space-y-2.5 text-sm">
              {Object.entries(summaryQuery.data.counts ?? {}).map(([k, v]) => (
                <li
                  key={k}
                  className="flex items-center justify-between border-b border-hairline pb-2 last:border-0 last:pb-0"
                >
                  <span className="flex items-center gap-2 text-stone">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: KIND_COLORS[k] ?? "#94a3b8" }}
                    />
                    {KIND_LABELS[k] ?? k}
                  </span>
                  <span className="font-display text-[18px] tabular-nums text-ink">
                    {v as number}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        ) : null}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty state — elegant constellation placeholder
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Lens switcher
// ---------------------------------------------------------------------------

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
            className={cn(
              "flex items-center gap-1.5 px-3.5 py-1.5 rounded-full transition-colors duration-180 ease-pirsch",
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

// ---------------------------------------------------------------------------
// Kind filters
// ---------------------------------------------------------------------------

function KindFilters({
  kinds,
  active,
  onToggle,
  onClear,
}: {
  kinds: string[];
  active: Set<string>;
  onToggle: (k: string) => void;
  onClear: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {kinds.map((k) => {
        const isActive = active.has(k);
        const color = KIND_COLORS[k] ?? "#94a3b8";
        return (
          <button
            key={k}
            type="button"
            onClick={() => onToggle(k)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors",
              isActive
                ? "border-ink/20 bg-ink/[0.04] text-ink"
                : "border-transparent text-ink/60 hover:text-ink",
            )}
          >
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: color }}
            />
            {KIND_LABELS[k] ?? k}
          </button>
        );
      })}
      {active.size > 0 ? (
        <Button
          size="sm"
          variant="ghost"
          onClick={onClear}
          className="ml-1"
        >
          Limpiar
        </Button>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Outline lens — Tana-style flat list grouped by kind
// ---------------------------------------------------------------------------

function OutlineLens({
  snapshot,
  onFocusEntity,
}: {
  snapshot: GraphSnapshot;
  onFocusEntity: (id: string, kind: string, label: string) => void;
}) {
  const grouped = useMemo(() => {
    const map = new Map<string, GraphSnapshot["nodes"]>();
    for (const node of snapshot.nodes) {
      const list = map.get(node.attributes.kind) ?? [];
      list.push(node);
      map.set(node.attributes.kind, list);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [snapshot]);

  if (grouped.length === 0) {
    return (
      <p className="text-sm text-ink/50 italic">
        Aún no hay entradas. Empieza a conversar para construir tu universo.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {grouped.map(([kind, items]) => (
        <section key={kind}>
          <header className="flex items-center gap-2 mb-2">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: KIND_COLORS[kind] ?? "#94a3b8" }}
            />
            <h3 className="text-sm font-semibold text-ink">
              {KIND_LABELS[kind] ?? kind}
            </h3>
            <Badge tone="stone" className="ml-auto text-xs">
              {items.length}
            </Badge>
          </header>
          <ul className="ml-4 space-y-1">
            {items.map((item) => (
              <li
                key={item.key}
                className="group flex items-center gap-2 py-0.5"
              >
                <button
                  type="button"
                  onClick={() =>
                    onFocusEntity(item.key, kind, item.attributes.label)
                  }
                  className="text-left text-sm text-ink/80 hover:text-ink truncate"
                >
                  {item.attributes.label}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Trajectory lens — chronological placeholder (Sprint R adds the slider)
// ---------------------------------------------------------------------------

function TrajectoryLens({ snapshot }: { snapshot: GraphSnapshot | null }) {
  if (!snapshot) {
    return (
      <p className="text-sm text-ink/50 italic">
        Cargando trayectoria…
      </p>
    );
  }
  // Sprint Q ships a basic list; Sprint R wires it to the temporal
  // valid_from/valid_to properties + the Episode nodes for a full
  // timeline.
  return (
    <div className="space-y-3 text-sm text-ink/70">
      <p>
        Aquí aparecerá tu trayectoria temporal — episodios de chat,
        skills adquiridos, hitos. (Sprint R completa la línea de tiempo
        navegable.)
      </p>
      <p className="text-xs text-ink/50">
        Snapshot actual: {snapshot.node_count} nodos · {snapshot.edge_count} aristas.
      </p>
    </div>
  );
}
