/**
 * HomePage = the authenticated landing surface.
 *
 * Desktop ≥1024px: 3-col layout (top-nav from Layout) | chat centered | widget pane right.
 * Mobile <1024px:  full-width chat + FAB bottom-right that opens the WidgetPane in a Vaul bottom-sheet.
 *
 * The chat itself is centered (max-w ~680px) so it stops feeling "big and flat";
 * widgets accumulate in the right pane via `present_widget` (see chat/actions.tsx).
 */
import { Suspense, lazy, useEffect, useState } from "react";
import { Sparkles, PanelRightOpen, LayoutGrid } from "lucide-react";
import { Drawer } from "vaul";
import { UniverseDrawer } from "@/chat/UniverseDrawer";
import { WidgetPane } from "@/chat/WidgetPane";
import { useChatState } from "@/chat/state";
import { Button, Skeleton } from "@/ui";
import { tour } from "@/app/tour/TourProvider";
import { firstRunTour } from "@/app/tour/tours";
import { enableCopilot, useCopilotReady } from "@/app/CopilotProvider";

// Trigger CopilotKit dynamic import as soon as the chat surface is loaded.
enableCopilot();

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
  const ready = useCopilotReady();
  const widgetsCount = useChatState((s) => s.widgets.length);

  // First-run tour — only on the chat surface, only once per user.
  useEffect(() => {
    if (!tour.isCompleted(firstRunTour.id)) {
      const t = setTimeout(() => tour.start(firstRunTour), 600);
      return () => clearTimeout(t);
    }
  }, []);

  return (
    <div className="fixed inset-0 top-16 bottom-16 md:bottom-0 flex bg-canvas">
      {/* Chat column — centered on desktop within its share of the row */}
      <div className="flex-1 min-w-0 flex flex-col">
        <div
          data-tour="home-chat-header"
          className="flex items-center justify-between bg-canvas/80 backdrop-blur-md px-4 md:px-6 py-3 bg-gradient-to-b from-canvas to-canvas/60"
        >
          <div className="flex items-center gap-2.5">
            <span
              aria-hidden
              className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-leaf-soft text-leaf-ink"
            >
              <Sparkles size={14} />
            </span>
            <div className="leading-tight">
              <div className="text-sm font-medium text-ink">Tu universo profesional</div>
              <div className="text-[11px] text-stone">Conversación con tu agente</div>
            </div>
          </div>
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
        </div>
        <div className="flex-1 min-h-0 bg-canvas chat-surface-area">
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
        </div>
      </div>

      {/* Widget pane — desktop only */}
      <aside className="hidden lg:flex w-[360px] xl:w-[400px] border-l border-ink/5 flex-col">
        <WidgetPane />
      </aside>

      {/* Mobile FAB to open widgets as a bottom-sheet */}
      <button
        type="button"
        onClick={() => setWidgetsSheetOpen(true)}
        className="lg:hidden fixed bottom-20 right-4 z-30 inline-flex items-center gap-2 pl-3 pr-4 h-11 rounded-full bg-ink text-canvas shadow-lift hover:-translate-y-[1px] transition-transform focus-visible:ring-2 focus-visible:ring-ink/30 focus-visible:ring-offset-2 focus-visible:outline-none"
        aria-label="Abrir panel de widgets"
      >
        <LayoutGrid size={16} />
        <span className="text-sm font-medium">
          Widgets{widgetsCount > 0 ? ` · ${widgetsCount}` : ""}
        </span>
      </button>

      <Drawer.Root
        open={widgetsSheetOpen}
        onOpenChange={(v: boolean) => setWidgetsSheetOpen(v)}
      >
        <Drawer.Portal>
          <Drawer.Overlay className="fixed inset-0 bg-ink/30 backdrop-blur-sm z-40 lg:hidden" />
          <Drawer.Content className="bg-canvas text-ink flex flex-col fixed bottom-0 left-0 right-0 z-50 h-[85vh] rounded-t-card shadow-lift lg:hidden">
            <Drawer.Title className="sr-only">Widgets</Drawer.Title>
            <div className="mx-auto mt-2 h-1 w-10 rounded-full bg-ink/15" aria-hidden />
            <div className="flex-1 min-h-0">
              <WidgetPane compact />
            </div>
          </Drawer.Content>
        </Drawer.Portal>
      </Drawer.Root>

      <UniverseDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  );
}

function ChatLoadingSkeleton() {
  return (
    <div className="flex flex-col h-full p-4 md:p-6 gap-3 max-w-[680px] mx-auto w-full">
      <div className="flex-1 flex flex-col gap-3 overflow-hidden">
        <Skeleton shape="block" className="h-12 max-w-[60%]" />
        <Skeleton shape="block" className="h-20 max-w-[75%] ml-auto" />
        <Skeleton shape="block" className="h-16 max-w-[70%]" />
      </div>
      <Skeleton shape="block" className="h-12" />
    </div>
  );
}
