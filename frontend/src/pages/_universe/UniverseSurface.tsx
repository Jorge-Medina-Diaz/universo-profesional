/**
 * UniverseSurface — the single canonical universe surface, in two modes.
 *
 * The home (`/`) and universe (`/universe`) routes were "mostly the same page":
 * a full-bleed constellation shell + a GraphView + the agent chat. They now
 * share one implementation. The genuinely-different chrome is the only thing
 * that branches on `mode`:
 *   • ambient   — the home: dimmed ambient graph behind a hero + composer.
 *   • workspace — the interactive graph + controls rail + lenses + inspector.
 *
 * Everything shared (the shell, the agent chat mount, the loading skeleton, the
 * GraphView) lives in reused modules — no duplication between the two routes.
 */
import { Suspense, lazy, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "motion/react";
import { PanelRightOpen, LayoutGrid } from "lucide-react";
import { useChatState } from "@/chat/state";
import { nudges, useAuthStore } from "@/shared/api";
import { graphApi, type GraphSnapshot } from "@/graph/api";
import { AgentChatMount } from "@/chat/AgentChatMount";
import { Button, GalaxyIllustration } from "@/ui";
import { tour } from "@/app/tour/TourProvider";
import { firstRunTour } from "@/app/tour/tours";
import { queryKeys } from "@/shared/queryKeys";
import { UniverseWorkspace } from "./UniverseWorkspace";

export type UniverseMode = "ambient" | "workspace";

const GraphView = lazy(() =>
  import("@/graph/GraphView").then((m) => ({ default: m.GraphView })),
);
const WidgetsSheet = lazy(() =>
  import("@/chat/WidgetsSheet").then((m) => ({ default: m.WidgetsSheet })),
);

export function UniverseSurface({ mode }: { mode: UniverseMode }) {
  if (mode === "workspace") return <UniverseWorkspace />;
  return <AmbientUniverse />;
}

/** Ambient "home" — the chat-first landing with a living constellation. */
function AmbientUniverse() {
  const [widgetsSheetOpen, setWidgetsSheetOpen] = useState(false);
  const chatExpanded = useChatState((s) => s.chatExpanded);
  const widgetsCount = useChatState((s) => s.widgets.length);

  const snapshot = useQuery({
    queryKey: queryKeys.graph.snapshot,
    queryFn: () => graphApi.snapshot(false),
    staleTime: 30_000,
  });

  // First-run tour — only on the home surface, only once per user.
  useEffect(() => {
    if (!tour.isCompleted(firstRunTour.id)) {
      const t = setTimeout(() => tour.start(firstRunTour), 700);
      return () => clearTimeout(t);
    }
  }, []);

  const hasNodes = (snapshot.data?.node_count ?? 0) > 0;

  return (
    <div className="fixed inset-0 top-16 bottom-16 md:bottom-0 overflow-hidden constellation-bg">
      {/* Constellation backdrop */}
      <div className="absolute inset-0 animate-drift">
        {hasNodes && snapshot.data ? (
          <Suspense
            fallback={
              <div className="flex h-full items-center justify-center opacity-40">
                <GalaxyIllustration className="text-ink" width={420} height={320} />
              </div>
            }
          >
            <GraphView snapshot={snapshot.data} ambient />
          </Suspense>
        ) : (
          <div className="flex h-full items-center justify-center opacity-40">
            <GalaxyIllustration className="text-ink" width={420} height={320} />
          </div>
        )}
      </div>

      <AmbientHero snapshot={snapshot.data ?? null} hasNodes={hasNodes} chatExpanded={chatExpanded} />

      {/* Floating controls — top right */}
      <div className="absolute top-4 right-4 z-30 flex items-center gap-2">
        <NudgeBadge />
        <Button
          size="sm"
          variant="outline"
          onClick={() => (window.location.hash = "#/universe")}
          trailingIcon={<PanelRightOpen size={14} />}
          data-tour="open-universe-button"
        >
          <span className="hidden sm:inline">Abrir universo</span>
          <span className="sm:hidden">Universo</span>
        </Button>
        <button
          type="button"
          onClick={() => setWidgetsSheetOpen(true)}
          className="relative inline-flex h-9 items-center gap-2 rounded-btn border border-hairline bg-canvas/90 pl-3 pr-3.5 text-stone backdrop-blur transition-colors hover:text-ink"
          aria-label="Panel de widgets"
        >
          <LayoutGrid size={15} />
          <span className="hidden text-sm sm:inline">Widgets</span>
          {widgetsCount > 0 && (
            <span className="grid h-[18px] min-w-[18px] place-items-center rounded-full bg-leaf px-1 text-[10px] font-medium text-ink">
              {widgetsCount}
            </span>
          )}
        </button>
      </div>

      {/* Shared agent chat (single mount; dock suppresses itself on "/"). */}
      <div data-tour="home-chat-header">
        <AgentChatMount />
      </div>

      <Suspense fallback={null}>
        <WidgetsSheet open={widgetsSheetOpen} onOpenChange={setWidgetsSheetOpen} />
      </Suspense>
    </div>
  );
}

/**
 * Subtle pill showing how many proactive nudges await — clicking expands the
 * agent chat, where the chips live above the composer. Plain TanStack query
 * (no CopilotKit hooks) so it's safe in this always-mounted shell.
 */
function NudgeBadge() {
  const authed = !!useAuthStore((s) => s.accessToken);
  const setChatExpanded = useChatState((s) => s.setChatExpanded);
  const nudgesQ = useQuery({
    queryKey: queryKeys.nudges.active,
    queryFn: () => nudges.active(),
    enabled: authed,
    staleTime: 5 * 60_000,
  });
  const count = nudgesQ.data?.nudges.length ?? 0;
  if (count === 0) return null;
  return (
    <button
      type="button"
      onClick={() => setChatExpanded(true)}
      aria-label={`${count} sugerencia${count > 1 ? "s" : ""} pendiente${count > 1 ? "s" : ""} — abrir chat`}
      className="inline-flex h-9 items-center gap-2 rounded-full border border-hairline bg-canvas/90 px-3.5 text-xs text-stone backdrop-blur transition-colors hover:text-ink"
    >
      <span
        aria-hidden
        className="h-1.5 w-1.5 rounded-full bg-nova shadow-[0_0_8px_var(--color-nova)]"
      />
      <span className="tabular-nums font-medium text-ink">{count}</span>
      pendiente{count > 1 ? "s" : ""}
    </button>
  );
}

/** The ambient hero — fades out when the chat expands. */
function AmbientHero({
  snapshot,
  hasNodes,
  chatExpanded,
}: {
  snapshot: GraphSnapshot | null;
  hasNodes: boolean;
  chatExpanded: boolean;
}) {
  return (
    <AnimatePresence>
      {!chatExpanded && (
        <motion.div
          key="hero"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.42, ease: [0.2, 0.8, 0.2, 1] }}
          className="pointer-events-none absolute inset-x-0 top-[16%] flex flex-col items-center px-6 text-center md:top-[20%]"
        >
          <span className="eyebrow mb-4 inline-flex items-center gap-1.5">
            <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-nova shadow-[0_0_8px_var(--color-nova)]" />
            Universo profesional
          </span>
          <h1 className="font-display text-display max-w-3xl text-ink">
            Tu carrera,{" "}
            <span className="bg-gradient-to-r from-[var(--color-sunbeam-yellow)] via-[var(--color-leafy-green)] to-[var(--color-nova)] bg-clip-text text-transparent">
              viva
            </span>
          </h1>
          <p className="text-body-lg mt-4 max-w-md text-stone">
            Habla con tu agente para construir y mantener tu universo. Cada
            conversación lo hace crecer.
          </p>
          {hasNodes && snapshot && (
            <span className="mt-5 inline-flex items-center gap-2 rounded-full border border-hairline bg-[color-mix(in_srgb,var(--surface-canvas)_70%,transparent)] px-3.5 py-1.5 text-xs text-stone backdrop-blur">
              <span className="font-medium tabular-nums text-ink">{snapshot.node_count}</span> entidades
              <span aria-hidden className="text-stone/40">·</span>
              <span className="font-medium tabular-nums text-ink">{snapshot.edge_count}</span> conexiones
            </span>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
