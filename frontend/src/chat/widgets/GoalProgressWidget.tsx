/**
 * GoalProgressWidget — list of active goals with sub-task progress bars.
 *
 * Data shape expected from the agent:
 *   { goals: [{
 *       id, horizon, title, description, status, target_date,
 *       details: { subtasks?: [{title, done}] },
 *       completed_at
 *     }] }
 *
 * If `goals` is not passed, falls back to nothing (the agent is expected
 * to call `list_goals` and pass the result; we don't fetch here).
 */
import { Target, CheckCircle2, Circle, Calendar } from "lucide-react";
import { Badge } from "@/ui";

type Subtask = { title: string; done?: boolean };

interface Goal {
  id?: string;
  horizon?: string;
  title?: string;
  description?: string | null;
  status?: string;
  target_date?: string | null;
  details?: { subtasks?: Subtask[] } | null;
  completed_at?: string | null;
}

interface GoalProgressWidgetData {
  goals?: Goal[];
}

const HORIZON_LABEL: Record<string, string> = {
  "3_months": "3 meses",
  "6_months": "6 meses",
  "1_year": "1 año",
  long_term: "largo plazo",
};

const STATUS_TONE: Record<string, "leaf" | "amber" | "stone" | "sunbeam"> = {
  active: "leaf",
  paused: "amber",
  completed: "sunbeam",
  dropped: "stone",
};

export function GoalProgressWidget({ data }: { data: GoalProgressWidgetData }) {
  const goals = data.goals ?? [];
  if (!goals.length) {
    return (
      <p className="text-sm text-stone">
        Aún no tienes metas activas. Cuéntale al agente qué quieres lograr — algo como{" "}
        <em>"quiero ser senior fullstack en 6 meses"</em>.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-3">
      {goals.map((g, i) => {
        const subtasks = g.details?.subtasks ?? [];
        const done = subtasks.filter((s) => s.done).length;
        const total = subtasks.length;
        const progress = total > 0 ? Math.round((100 * done) / total) : null;
        return (
          <li key={g.id ?? i} className="flex flex-col gap-2">
            <div className="flex items-start gap-2.5">
              <span
                aria-hidden
                className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-leaf-soft text-leaf-ink shrink-0 mt-0.5"
              >
                <Target size={14} />
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-start gap-2 flex-wrap">
                  <span className="text-sm font-medium text-ink leading-tight">
                    {g.title ?? "Meta"}
                  </span>
                  {g.horizon ? (
                    <Badge tone="stone" size="sm">
                      {HORIZON_LABEL[g.horizon] ?? g.horizon}
                    </Badge>
                  ) : null}
                  {g.status && g.status !== "active" ? (
                    <Badge tone={STATUS_TONE[g.status] ?? "stone"} size="sm">
                      {g.status}
                    </Badge>
                  ) : null}
                </div>
                {g.target_date ? (
                  <div className="text-xs text-stone flex items-center gap-1 mt-0.5">
                    <Calendar size={11} />
                    <span>{formatDate(g.target_date)}</span>
                  </div>
                ) : null}
                {g.description ? (
                  <p className="text-xs text-ink/70 mt-1 leading-snug">{g.description}</p>
                ) : null}
              </div>
            </div>
            {total > 0 ? (
              <>
                <div className="h-1.5 w-full rounded-full bg-black/[0.06] overflow-hidden">
                  <div
                    className="h-full bg-leaf transition-all duration-280"
                    style={{ width: `${progress}%` }}
                    role="progressbar"
                    aria-valuenow={progress ?? 0}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  />
                </div>
                <div className="text-[11px] text-stone -mt-0.5">
                  {done} de {total} sub-tareas · {progress}%
                </div>
                <ul className="flex flex-col gap-1 pl-1">
                  {subtasks.map((s, j) => (
                    <li
                      key={`${g.id}-${j}`}
                      className="flex items-center gap-2 text-xs text-ink/80"
                    >
                      {s.done ? (
                        <CheckCircle2 size={12} className="text-leaf-ink shrink-0" />
                      ) : (
                        <Circle size={12} className="text-stone shrink-0" />
                      )}
                      <span className={s.done ? "line-through text-stone" : ""}>
                        {s.title}
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString("es-ES", { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}
