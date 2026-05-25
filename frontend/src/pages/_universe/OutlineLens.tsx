/**
 * OutlineLens — an editorial table-of-contents of the universe.
 *
 * Leads with the profile "shape" (T-shape + strongest areas from
 * /universe/shape), then collapsible sections per kind with counts. Rows are
 * clickable → open the node detail drawer (via onSelect). Replaces the old flat
 * kind list.
 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";
import { api } from "@/shared/api";
import { KIND_COLORS, KIND_LABELS, DEFAULT_KIND_COLOR } from "@/shared/kindColors";
import { cn } from "@/ui";
import type { GraphSnapshot } from "@/graph/api";
import type { GraphSelection } from "@/graph/GraphView";

interface ShapeStrength {
  area: string;
  depth_years?: number;
  breadth_count?: number;
  confidence?: number;
  is_primary?: boolean;
}
interface ShapeResponse {
  ok: boolean;
  shape_type: string | null;
  primary_areas: string[];
  secondary_areas: string[];
  strengths: ShapeStrength[];
}

const SHAPE_LABEL: Record<string, string> = {
  "T-shape": "Perfil en T",
  "I-shape": "Especialista (I)",
  "pi-shape": "Perfil en π",
  "M-shape": "Polímata (M)",
  specialist: "Especialista",
  generalist: "Generalista",
};

export function OutlineLens({
  snapshot,
  onSelect,
}: {
  snapshot: GraphSnapshot;
  onSelect: (sel: GraphSelection) => void;
}) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

  const shapeQuery = useQuery({
    queryKey: ["universe", "shape"],
    staleTime: 60_000,
    retry: false,
    queryFn: () => api<ShapeResponse>("/api/v1/universe/shape"),
  });

  const grouped = useMemo(() => {
    const map = new Map<string, GraphSnapshot["nodes"]>();
    for (const node of snapshot.nodes) {
      const list = map.get(node.attributes.kind) ?? [];
      list.push(node);
      map.set(node.attributes.kind, list);
    }
    return Array.from(map.entries()).sort(([, a], [, b]) => b.length - a.length);
  }, [snapshot]);

  const shape = shapeQuery.data;
  const strengths = (shape?.strengths ?? []).filter((s) => s.area).slice(0, 6);

  if (grouped.length === 0) {
    return (
      <p className="text-sm text-ink/50 italic">
        Aún no hay entradas. Empieza a conversar para construir tu universo.
      </p>
    );
  }

  return (
    <div className="max-w-2xl space-y-7">
      {/* Shape header */}
      {(shape?.shape_type && shape.shape_type !== "none") || strengths.length > 0 ? (
        <div className="rounded-card border border-hairline bg-surface/40 p-5">
          <p className="eyebrow mb-1">Forma de tu perfil</p>
          <h3 className="font-display text-[22px] leading-tight text-ink">
            {shape?.shape_type && shape.shape_type !== "none"
              ? SHAPE_LABEL[shape.shape_type] ?? shape.shape_type
              : "Tus áreas fuertes"}
          </h3>
          {strengths.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {strengths.map((s) => (
                <span
                  key={s.area}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs",
                    s.is_primary
                      ? "border-leaf/40 bg-leaf/10 text-leaf-ink"
                      : "border-hairline text-stone",
                  )}
                >
                  {s.area}
                  {typeof s.depth_years === "number" && s.depth_years > 0 && (
                    <span className="tabular-nums opacity-70">{s.depth_years.toFixed(0)}a</span>
                  )}
                </span>
              ))}
            </div>
          )}
        </div>
      ) : null}

      {/* Sections per kind */}
      <div className="space-y-3">
        {grouped.map(([kind, items]) => {
          const isCollapsed = collapsed.has(kind);
          return (
            <section key={kind} className="rounded-card border border-hairline overflow-hidden">
              <button
                type="button"
                onClick={() =>
                  setCollapsed((prev) => {
                    const next = new Set(prev);
                    if (next.has(kind)) next.delete(kind);
                    else next.add(kind);
                    return next;
                  })
                }
                className="flex w-full items-center gap-2.5 bg-surface/30 px-4 py-2.5 text-left hover:bg-surface/60 transition-colors"
              >
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: KIND_COLORS[kind] ?? DEFAULT_KIND_COLOR }}
                />
                <h3 className="text-sm font-semibold text-ink">{KIND_LABELS[kind] ?? kind}</h3>
                <span className="ml-auto rounded-full bg-ink/[0.06] px-2 py-0.5 text-xs tabular-nums text-stone">
                  {items.length}
                </span>
                <ChevronDown
                  size={15}
                  className={cn(
                    "text-stone transition-transform duration-200",
                    isCollapsed && "-rotate-90",
                  )}
                />
              </button>
              {!isCollapsed && (
                <ul className="divide-y divide-hairline/60">
                  {items.map((item) => (
                    <li key={item.key}>
                      <button
                        type="button"
                        onClick={() =>
                          onSelect({
                            id: item.key,
                            kind,
                            label: item.attributes.label,
                          })
                        }
                        className="block w-full truncate px-4 py-2 text-left text-sm text-ink/80 hover:bg-surface/50 hover:text-ink transition-colors"
                      >
                        {item.attributes.label}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
