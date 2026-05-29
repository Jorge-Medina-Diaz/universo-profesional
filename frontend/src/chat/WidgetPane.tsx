/**
 * WidgetPane — vertical stack of widgets the agent has summoned via
 * `present_widget` during the session. Lives at the right side of HomePage
 * on desktop, and inside a Vaul bottom-sheet on mobile.
 *
 * Pinned widgets render first (sorted by createdAt desc within group);
 * unpinned below in chronological order. New widgets auto-scroll into view.
 */
import { useEffect, useMemo, useRef } from "react";
import { AnimatePresence } from "motion/react";
import { Sparkles, Trash2 } from "lucide-react";
import { useChatState, type ChatWidget } from "@/chat/state";
import { WidgetShell } from "./widgets/WidgetShell";
import { getWidgetComponent } from "./widgets/registry";
import { GalaxyIllustration } from "@/ui/illustrations";

interface WidgetPaneProps {
  className?: string;
  /** When true, show a compact header (mobile bottom-sheet uses this). */
  compact?: boolean;
}

export function WidgetPane({ className, compact = false }: WidgetPaneProps) {
  const widgets = useChatState((s) => s.widgets);
  const removeWidget = useChatState((s) => s.removeWidget);
  const togglePin = useChatState((s) => s.togglePin);
  const clearWidgets = useChatState((s) => s.clearWidgets);

  const listRef = useRef<HTMLDivElement>(null);
  const previousLastId = useRef<string | null>(null);

  const ordered = useMemo(() => orderWidgets(widgets), [widgets]);
  const lastId = ordered[ordered.length - 1]?.id ?? null;

  // Auto-scroll to the newest non-pinned widget when one arrives.
  useEffect(() => {
    if (!lastId || lastId === previousLastId.current) return;
    previousLastId.current = lastId;
    const el = listRef.current?.querySelector<HTMLElement>(
      `[data-widget-id="${lastId}"]`,
    );
    el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [lastId]);

  return (
    <div className={["flex flex-col h-full bg-canvas/60", className].filter(Boolean).join(" ")}>
      <div
        className={[
          "flex items-center justify-between gap-2 px-4 border-b border-ink/5 bg-canvas/80 backdrop-blur-md",
          compact ? "py-2.5" : "py-3",
        ].join(" ")}
      >
        <div className="flex items-center gap-2.5">
          <span
            aria-hidden
            className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-sunbeam-soft text-sunbeam-ink"
          >
            <Sparkles size={14} />
          </span>
          <div className="leading-tight">
            <div className="text-sm font-medium text-ink">Widgets</div>
            <div className="text-[11px] text-stone">
              {widgets.length === 0
                ? "Vacío — pídele al agente"
                : `${widgets.length} en sesión`}
            </div>
          </div>
        </div>
        {widgets.length > 0 ? (
          <button
            type="button"
            onClick={clearWidgets}
            className="inline-flex items-center gap-1 text-xs text-stone hover:text-ink transition-colors px-2 py-1 rounded-btn hover:bg-ink/[0.04] focus-visible:ring-2 focus-visible:ring-ink/20 focus-visible:ring-offset-1 focus-visible:outline-none"
            aria-label="Limpiar todos los widgets"
          >
            <Trash2 size={12} />
            <span>Limpiar</span>
          </button>
        ) : null}
      </div>

      <div ref={listRef} className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
        {ordered.length === 0 ? <EmptyState /> : null}
        <AnimatePresence initial={false}>
          {ordered.map((w) => {
            const Comp = getWidgetComponent(w.kind);
            return (
              <div key={w.id} data-widget-id={w.id}>
                <WidgetShell
                  widget={w}
                  onRemove={removeWidget}
                  onTogglePin={togglePin}
                >
                  {Comp ? (
                    <Comp data={w.data} />
                  ) : (
                    <UnknownWidget kind={w.kind} />
                  )}
                </WidgetShell>
              </div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center px-6 py-10 gap-4">
      <GalaxyIllustration className="w-24 h-24 opacity-70" />
      <div className="max-w-[260px]">
        <h3 className="text-sm font-medium text-ink mb-1">Tu panel está vacío</h3>
        <p className="text-xs text-stone leading-relaxed">
          Cuando le pidas al agente cosas como <em>"muéstrame mis skills"</em> o{" "}
          <em>"lista mis certificados"</em>, aparecerán aquí como widgets que
          puedes anclar o cerrar.
        </p>
      </div>
    </div>
  );
}

function UnknownWidget({ kind }: { kind: string }) {
  return (
    <p className="text-sm text-stone">
      Widget de tipo <code className="text-xs">{kind}</code> aún no soportado.
    </p>
  );
}

function orderWidgets(items: ChatWidget[]): ChatWidget[] {
  const pinned: ChatWidget[] = [];
  const rest: ChatWidget[] = [];
  for (const w of items) (w.pinned ? pinned : rest).push(w);
  // Pinned: newest first within pinned. Rest: oldest-first (so scroll
  // brings the newest near the bottom and auto-scroll lands on it).
  pinned.sort((a, b) => b.createdAt - a.createdAt);
  rest.sort((a, b) => a.createdAt - b.createdAt);
  return [...pinned, ...rest];
}
