/**
 * TrajectoryLens — a real editorial timeline of the user's dated entities
 * (experiences, education, projects, certifications, courses, achievements),
 * replacing the old placeholder. Events are grouped by year on a vertical
 * spine, colored by kind, with duration + "Actual" markers. Clicking an event
 * opens the node detail drawer (via onSelect).
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Stagger } from "@/ui/motion";
import { universe } from "@/shared/api";
import { KIND_COLORS, KIND_LABELS } from "@/shared/kindColors";
import type { GraphSelection } from "@/graph/GraphView";

interface TimelineEvent {
  id: string;
  kind: string;
  title: string;
  subtitle: string;
  start: Date | null;
  end: Date | null;
  isCurrent: boolean;
}

const DATED_KINDS = [
  "experience",
  "education",
  "project",
  "certification",
  "course",
  "achievement",
] as const;

function parseDate(v: unknown): Date | null {
  if (!v) return null;
  const d = new Date(String(v));
  return Number.isNaN(d.getTime()) ? null : d;
}

function toEvent(kind: string, row: Record<string, unknown>): TimelineEvent | null {
  const id = String(row.id ?? "");
  if (!id) return null;
  const isCurrent = Boolean(row.is_current);
  let title = "";
  let subtitle = "";
  let start: Date | null = null;
  let end: Date | null = null;
  switch (kind) {
    case "experience":
      title = String(row.role ?? "Experiencia");
      subtitle = String(row.organization ?? "");
      start = parseDate(row.start_date);
      end = parseDate(row.end_date);
      break;
    case "education":
      title = String(row.degree ?? "Formación");
      subtitle = String(row.institution ?? "");
      start = parseDate(row.start_date);
      end = parseDate(row.end_date);
      break;
    case "project":
      title = String(row.name ?? "Proyecto");
      subtitle = String(row.role ?? row.project_type ?? "");
      start = parseDate(row.start_date);
      end = parseDate(row.end_date);
      break;
    case "certification":
      title = String(row.name ?? "Certificación");
      subtitle = String(row.issuer ?? "");
      start = parseDate(row.issued_on);
      end = parseDate(row.expires_on);
      break;
    case "course":
      title = String(row.title ?? "Curso");
      subtitle = String(row.platform ?? "");
      start = parseDate(row.started_on);
      end = parseDate(row.completed_on);
      break;
    case "achievement":
      title = String(row.title ?? "Logro");
      subtitle = String(row.context ?? "");
      start = parseDate(row.achieved_on);
      break;
  }
  return { id, kind, title, subtitle, start, end, isCurrent };
}

function fmtMonth(d: Date | null): string {
  if (!d) return "";
  return d.toLocaleDateString("es-ES", { month: "short", year: "numeric" });
}

function durationLabel(e: TimelineEvent): string {
  const from = fmtMonth(e.start);
  const to = e.isCurrent ? "Actual" : fmtMonth(e.end);
  if (from && to) return `${from} — ${to}`;
  return from || to || "";
}

export function TrajectoryLens({
  onSelect,
}: {
  onSelect: (sel: GraphSelection) => void;
}) {
  const query = useQuery({
    queryKey: ["trajectory"],
    staleTime: 30_000,
    queryFn: async () => {
      const results = await Promise.all(
        DATED_KINDS.map(async (kind) => {
          try {
            const rows = (await universe.list(kind)) as Record<string, unknown>[];
            return rows.map((r) => toEvent(kind, r)).filter((e): e is TimelineEvent => !!e);
          } catch {
            return [] as TimelineEvent[];
          }
        }),
      );
      return results.flat();
    },
  });

  const grouped = useMemo(() => {
    const events = (query.data ?? [])
      .filter((e) => e.start)
      .sort((a, b) => (b.start!.getTime() ?? 0) - (a.start!.getTime() ?? 0));
    const byYear = new Map<number, TimelineEvent[]>();
    for (const e of events) {
      const y = e.isCurrent ? new Date().getFullYear() : e.start!.getFullYear();
      const list = byYear.get(y) ?? [];
      list.push(e);
      byYear.set(y, list);
    }
    return Array.from(byYear.entries()).sort(([a], [b]) => b - a);
  }, [query.data]);

  if (query.isLoading) {
    return <p className="text-sm text-stone">Construyendo tu trayectoria…</p>;
  }
  if (grouped.length === 0) {
    return (
      <p className="text-sm text-ink/50 italic">
        Aún no hay hitos con fecha. Cuéntale al agente tus experiencias, estudios o
        proyectos y aparecerán aquí en orden cronológico.
      </p>
    );
  }

  return (
    <div className="relative max-w-2xl">
      {/* spine */}
      <div className="absolute left-[7px] top-2 bottom-2 w-px bg-hairline" aria-hidden />
      <Stagger className="space-y-8">
        {grouped.map(([year, events]) => (
          <div key={year} className="relative">
              <div className="mb-3 flex items-center gap-3 pl-6">
                <span className="font-display text-[22px] leading-none text-ink tabular-nums">
                  {year}
                </span>
                <span className="h-px flex-1 bg-hairline" />
              </div>
              <ul className="space-y-2.5">
                {events.map((e) => (
                  <li key={`${e.kind}-${e.id}`} className="relative pl-6">
                    <span
                      className="absolute left-0 top-3 h-3.5 w-3.5 -translate-x-1/2 rounded-full ring-4 ring-canvas"
                      style={{ backgroundColor: KIND_COLORS[e.kind] ?? "#94a3b8", left: "7px" }}
                    />
                    <button
                      type="button"
                      onClick={() => onSelect({ id: e.id, kind: e.kind, label: e.title })}
                      className="group block w-full rounded-card border border-hairline bg-surface/40 px-4 py-3 text-left transition-all hover:border-ink/15 hover:bg-surface hover:-translate-y-px"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] uppercase tracking-wide text-stone">
                          {KIND_LABELS[e.kind] ?? e.kind}
                        </span>
                        {e.isCurrent && (
                          <span className="rounded-full bg-leaf/15 px-1.5 py-0.5 text-[10px] font-medium text-leaf-ink">
                            Actual
                          </span>
                        )}
                        <span className="ml-auto text-xs text-stone tabular-nums">
                          {durationLabel(e)}
                        </span>
                      </div>
                      <p className="mt-1 font-medium text-ink leading-snug group-hover:text-ink">
                        {e.title}
                      </p>
                      {e.subtitle && (
                        <p className="text-sm text-stone leading-snug">{e.subtitle}</p>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
        ))}
      </Stagger>
    </div>
  );
}
