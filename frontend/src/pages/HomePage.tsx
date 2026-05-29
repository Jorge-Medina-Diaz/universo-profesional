/**
 * HomePage = the authenticated landing surface.
 *
 * The home IS the universe: a live constellation backdrop with a floating,
 * expandable chat composer docked at the bottom (Claude/Typeform style).
 * Focusing the composer expands it into the full agentic chat; the
 * constellation dims behind. Widgets and the full universe stay one tap away.
 */
import { Suspense, lazy, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "motion/react";
import { PanelRightOpen, LayoutGrid } from "lucide-react";
import { UniverseDrawer } from "@/chat/UniverseDrawer";
import { FloatingChat } from "@/chat/FloatingChat";
import { useChatState } from "@/chat/state";
import { graphApi } from "@/graph/api";
import { Button, GalaxyIllustration } from "@/ui";
import { tour } from "@/app/tour/TourProvider";
import { firstRunTour } from "@/app/tour/tours";
import { enableCopilot, useCopilotReady } from "@/app/CopilotProvider";
import { queryKeys } from "@/shared/queryKeys";

const GraphView = lazy(() =>
  import("@/graph/GraphView").then((m) => ({ default: m.GraphView })),
);

const WidgetsSheet = lazy(() =>
  import("@/chat/WidgetsSheet").then((m) => ({ default: m.WidgetsSheet })),
);

const CopilotSurface = lazy(() =>
  import("./_chat/CopilotSurface").then((m) => ({ default: m.CopilotSurface })),
);

const SYSTEM_INSTRUCTIONS = `Eres el compañero agéntico del usuario.
Habla en español por defecto y en inglés si el usuario te lo pide.
Tu trabajo es ENTENDER, ESTRUCTURAR y MANTENER su universo profesional a lo largo del tiempo.

REGLAS:
1. Coherencia primero. Antes de proponer algo nuevo, considera si es una actualización de algo existente.
   El motor de upsert decidirá merge vs new — tú solo pasa los datos.
2. Una pregunta por turno. Si te describe varias cosas, despiézalas y rutea al specialist correspondiente.
3. Captura narrativa libre (opiniones, lo que está aprendiendo, gustos) en notes; datos estructurados
   en universe entities; documentos largos en knowledge.
4. NUNCA guardes sin confirmación: usa las propose_* tools que muestran cards en el chat.
5. Cuando detectes que pasó tiempo, pregunta proactivamente por evolución (¿sigues en X?, ¿completaste Y?).
6. Si el usuario menciona varias skills relacionadas en un solo turno (un stack, "trabajo con X/Y/Z"),
   usa propose_skill_batch en lugar de varias propose_skill — el usuario las confirma de golpe.
7. Cuando el usuario pegue una oferta o URL de empleo, llama a la tool MCP match_job_to_profile
   y después invoca present_job_match con el resultado para mostrar la scorecard visual.
8. Cuando el usuario quiera VER / EXPLORAR su universo (sus skills, proyectos, experiencias y
   cómo se conectan), usa \`universe_retrieve\` para encontrar los nodos relevantes y luego
   \`present_graph_view(mode)\` para mostrar el grafo navegable (focus | cluster | timeline |
   ontology_overlay). El universo ya no se muestra como listas planas, sino como grafo en
   /universe. Para vistas analíticas derivadas (radar de tecnologías, cobertura de signals,
   match de empleo, progreso de metas) usa \`present_widget\` con uno de sus kinds: tech_radar,
   signal_coverage, job_match, goals_progress, interview_qa, cloud_coverage, data_stack_topology,
   security_posture, architecture_patterns, portfolio_radar, learning_trajectory, agent_patterns,
   document_preview.`;

const INITIAL_MESSAGE = `Hola. Soy tu compañero para construir y mantener tu universo profesional. ¿Por dónde quieres empezar?`;

export function HomePage() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [widgetsSheetOpen, setWidgetsSheetOpen] = useState(false);
  const [chatExpanded, setChatExpanded] = useState(false);
  const ready = useCopilotReady();
  const widgetsCount = useChatState((s) => s.widgets.length);

  const snapshot = useQuery({
    queryKey: queryKeys.graph.snapshot,
    queryFn: () => graphApi.snapshot(false),
    staleTime: 30_000,
  });

  // Warm up CopilotKit only when this surface actually mounts.
  useEffect(() => {
    enableCopilot();
  }, []);

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
                <GalaxyIllustration width={420} height={320} />
              </div>
            }
          >
            <GraphView snapshot={snapshot.data} ambient />
          </Suspense>
        ) : (
          <div className="flex h-full items-center justify-center opacity-40">
            <GalaxyIllustration width={420} height={320} />
          </div>
        )}
      </div>

      {/* Hero — fades out when the chat expands */}
      <AnimatePresence>
        {!chatExpanded && (
          <motion.div
            key="hero"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.42, ease: [0.2, 0.8, 0.2, 1] }}
            className="absolute inset-x-0 top-[16%] md:top-[20%] flex flex-col items-center text-center px-6 pointer-events-none"
          >
            <span className="eyebrow mb-4">Universo profesional</span>
            <h1 className="font-display text-display text-ink max-w-3xl">
              Tu carrera, viva
            </h1>
            <p className="mt-4 max-w-md text-body-lg text-stone">
              Habla con tu agente para construir y mantener tu universo. Cada
              conversación lo hace crecer.
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating controls — top right */}
      <div className="absolute top-4 right-4 z-30 flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => setDrawerOpen(true)}
          trailingIcon={<PanelRightOpen size={14} />}
          data-tour="open-universe-button"
        >
          <span className="hidden sm:inline">Abrir universo</span>
          <span className="sm:hidden">Universo</span>
        </Button>
        <button
          type="button"
          onClick={() => setWidgetsSheetOpen(true)}
          className="relative inline-flex items-center gap-2 h-9 pl-3 pr-3.5 rounded-btn border border-hairline bg-canvas/90 backdrop-blur text-stone hover:text-ink transition-colors"
          aria-label="Panel de widgets"
        >
          <LayoutGrid size={15} />
          <span className="hidden sm:inline text-sm">Widgets</span>
          {widgetsCount > 0 && (
            <span className="grid place-items-center min-w-[18px] h-[18px] px-1 rounded-full bg-leaf text-[10px] font-medium text-ink">
              {widgetsCount}
            </span>
          )}
        </button>
      </div>

      {/* Floating chat composer (expands into the full surface) */}
      <div data-tour="home-chat-header">
        <FloatingChat onExpandedChange={setChatExpanded}>
          {ready ? (
            <Suspense fallback={<ChatLoadingSkeleton />}>
              <CopilotSurface
                instructions={SYSTEM_INSTRUCTIONS}
                title="Universo profesional"
                initial={INITIAL_MESSAGE}
              />
            </Suspense>
          ) : (
            <ChatLoadingSkeleton />
          )}
        </FloatingChat>
      </div>

      {/* Widgets bottom-sheet (all sizes — widgets accumulate via present_widget) */}
      <Suspense fallback={null}>
        <WidgetsSheet open={widgetsSheetOpen} onOpenChange={setWidgetsSheetOpen} />
      </Suspense>

      <UniverseDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  );
}

function ChatLoadingSkeleton() {
  return (
    <div className="flex flex-col h-full p-4 gap-4 max-w-[680px] mx-auto w-full justify-end">
      <div className="flex gap-3 animate-pulse">
        <div className="w-7 h-7 rounded-full bg-ink/10 shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-3 rounded bg-ink/10 w-3/4" />
          <div className="h-3 rounded bg-ink/10 w-1/2" />
        </div>
      </div>
      <div className="flex gap-3 justify-end animate-pulse">
        <div className="flex-1 space-y-2 max-w-[70%]">
          <div className="h-3 rounded bg-ink/10 w-full" />
          <div className="h-3 rounded bg-ink/10 w-2/3" />
        </div>
        <div className="w-7 h-7 rounded-full bg-ink/10 shrink-0" />
      </div>
      <div className="flex gap-3 animate-pulse">
        <div className="w-7 h-7 rounded-full bg-ink/10 shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-3 rounded bg-ink/10 w-5/6" />
          <div className="h-3 rounded bg-ink/10 w-4/5" />
          <div className="h-3 rounded bg-ink/10 w-1/3" />
        </div>
      </div>
      <div className="mt-2 h-10 rounded-xl bg-ink/[0.08]" />
    </div>
  );
}
