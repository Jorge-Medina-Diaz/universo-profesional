/**
 * SidebarContent — the universe workspace rail (desktop aside + mobile sheet).
 *
 * Extracted from UniversePage and reordered so the graph CONTROLS come first
 * (filters → display → legend), with the "state of your universe" widget
 * (UniverseProgress, which merges the old DiscoveryProgress + ProfileCompleteness)
 * and suggestions below. Cards use the DS `Card` primitive on the 8px grid
 * (gap-4 / p-4) instead of ad-hoc `rounded-card border bg-surface p-3` repeats.
 */
import { Card, Switch, cn } from "@/ui";
import { SuggestionBar } from "@/widgets/SuggestionBar";
import { UniverseProgress } from "@/widgets/UniverseProgress";
import { KIND_COLORS, KIND_LABELS, DEFAULT_KIND_COLOR } from "@/shared/kindColors";
import type { GraphSnapshot, CareerPillar } from "@/graph/api";

type Lens = "graph" | "outline" | "trajectory";

export interface SidebarContentProps {
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

export function SidebarContent({
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
  const isGraph = lens === "graph";
  return (
    <div className="flex flex-col gap-4">
      {/* Filters — the primary control, first. */}
      <Card padding="sm" className="border border-hairline">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium text-ink">Filtrar por tipo</span>
          {activeKinds.size > 0 && (
            <button
              type="button"
              onClick={onClearKinds}
              className="text-[11px] text-stone transition-colors hover:text-ink"
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
        />
      </Card>

      {/* Graph display toggles */}
      {isGraph && (
        <Card padding="sm" className="space-y-2.5 border border-hairline">
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
        </Card>
      )}

      {/* Legend */}
      {isGraph && legend.length > 0 && filteredSnapshot && (
        <Card padding="sm" className="border border-hairline">
          <span className="mb-2 block text-xs font-medium text-stone">Leyenda</span>
          <div className="flex flex-wrap gap-x-3 gap-y-1.5">
            {legend.map((g) => (
              <span key={g.key} className="inline-flex items-center gap-1.5 text-[11px] text-ink/80">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: g.color }} />
                {g.label}
              </span>
            ))}
          </div>
          <p className="mt-1.5 border-t border-hairline pt-1.5 text-[11px] text-stone">
            {filteredSnapshot.node_count} nodos · {filteredSnapshot.edge_count} aristas
          </p>
        </Card>
      )}

      {/* State of your universe — completeness + growth (merged widget). */}
      <UniverseProgress />

      <SuggestionBar />

      {pillars && pillars.length > 0 && (
        <Card padding="sm" className="border border-hairline">
          <span className="eyebrow">Pilares de carrera</span>
          <ul className="mt-3 space-y-3">
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

/** Kind filters with per-type counts. */
function KindFilters({
  kinds,
  counts,
  active,
  onToggle,
}: {
  kinds: string[];
  counts: Map<string, number>;
  active: Set<string>;
  onToggle: (k: string) => void;
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
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
            {KIND_LABELS[k] ?? k}
            <span className={cn("text-[10px] tabular-nums", isActive ? "text-ink/70" : "text-stone/60")}>
              {count}
            </span>
          </button>
        );
      })}
    </div>
  );
}
