/**
 * LearningTrajectoryWidget — chronological timeline of learning + artifacts + signals.
 *
 * Data: {
 *   items?: [{ when, kind, title, area }],
 *   areas_added_last_year?: string[],
 *   signals_acquired_last_year?: number,
 * }
 */
import { Badge } from "@/ui";
import { Sparkles, BookOpen, FolderGit2, FileText, Award, Mic } from "lucide-react";

interface TrajectoryItem {
  when?: string;
  kind?: string;
  title?: string;
  area?: string;
}

interface LearningTrajectoryData {
  items?: TrajectoryItem[];
  areas_added_last_year?: string[];
  signals_acquired_last_year?: number;
}

const KIND_META: Record<string, { icon: React.ComponentType<{ size?: number }>; tone: string }> = {
  course: { icon: BookOpen, tone: "bg-sunbeam-soft text-sunbeam-ink" },
  project: { icon: FolderGit2, tone: "bg-leaf-soft text-leaf-ink" },
  artifact: { icon: FileText, tone: "bg-stone/15 text-ink" },
  signal: { icon: Sparkles, tone: "bg-purple-100 text-purple-800" },
  certification: { icon: Award, tone: "bg-amber-100 text-amber-800" },
  talk: { icon: Mic, tone: "bg-rose-100 text-rose-800" },
};

export function LearningTrajectoryWidget({
  data,
}: {
  data: LearningTrajectoryData;
}) {
  const items = data.items ?? [];
  if (!items.length) {
    return (
      <p className="text-sm text-stone">
        Aún sin trayectoria registrada. Cuéntale al agente qué has hecho este
        año (cursos, proyectos, talks) para que dibuje tu crecimiento.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {(data.areas_added_last_year?.length ||
        data.signals_acquired_last_year) ? (
        <div className="flex flex-wrap items-center gap-2 text-[11px]">
          {data.signals_acquired_last_year !== undefined ? (
            <Badge tone="leaf">
              +{data.signals_acquired_last_year} signals último año
            </Badge>
          ) : null}
          {data.areas_added_last_year?.length ? (
            <>
              <span className="text-stone">áreas:</span>
              {data.areas_added_last_year.map((a) => (
                <Badge key={a} tone="sunbeam">
                  {a}
                </Badge>
              ))}
            </>
          ) : null}
        </div>
      ) : null}

      <ol className="flex flex-col gap-2 relative pl-6">
        <span
          aria-hidden
          className="absolute left-[10px] top-2 bottom-2 w-px bg-black/[0.08]"
        />
        {items.map((it, i) => {
          const meta = KIND_META[it.kind ?? "signal"] ?? KIND_META.signal;
          const Icon = meta.icon;
          return (
            <li key={i} className="relative flex items-start gap-2">
              <span
                aria-hidden
                className={`absolute -left-[10px] flex items-center justify-center w-5 h-5 rounded-full ${meta.tone} border-2 border-surface`}
              >
                <Icon size={10} />
              </span>
              <div className="flex-1 min-w-0 pl-4">
                <div className="flex items-center gap-2 text-[10px] text-stone">
                  <span className="tabular-nums">{fmtDate(it.when)}</span>
                  {it.area ? (
                    <span className="uppercase tracking-wide">· {it.area}</span>
                  ) : null}
                </div>
                <div className="text-[12px] text-ink leading-snug">
                  {it.title ?? "—"}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function fmtDate(iso?: string): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString("es-ES", { year: "numeric", month: "short" });
  } catch {
    return iso;
  }
}
