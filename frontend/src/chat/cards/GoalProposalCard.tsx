/**
 * GoalProposalCard — HITL card to confirm a new goal.
 *
 * Shows agent's proposed title + horizon + target_date + sub-tasks, lets
 * the user edit any field before confirming. Returns the full payload to
 * the agent via `respond`.
 *
 * Sub-tasks are editable: add (Enter to commit), remove (X), or wipe by
 * leaving the list empty.
 */
import { useMemo, useState } from "react";
import { Target, Calendar, X, Plus } from "lucide-react";
import { Badge, Button, ChatMessageMotion, Input, Textarea, cn } from "@/ui";

type Horizon = "3_months" | "6_months" | "1_year" | "long_term";

const HORIZONS: { id: Horizon; label: string; help: string }[] = [
  { id: "3_months", label: "3 meses", help: "Concreto, pronto" },
  { id: "6_months", label: "6 meses", help: "Cambio relevante" },
  { id: "1_year", label: "1 año", help: "Proyecto vital" },
  { id: "long_term", label: "Largo plazo", help: "Visión 3+ años" },
];

export interface GoalProposalCardProps {
  initialTitle: string;
  initialHorizon: Horizon;
  initialDescription?: string;
  initialTargetDate?: string;
  initialSubtasks: string[];
  pending: boolean;
  onConfirm: (payload: {
    title: string;
    horizon: Horizon;
    description?: string;
    target_date?: string;
    subtasks: string[];
  }) => void | Promise<void>;
  onCancel: () => void;
}

export function GoalProposalCard({
  initialTitle,
  initialHorizon,
  initialDescription,
  initialTargetDate,
  initialSubtasks,
  pending,
  onConfirm,
  onCancel,
}: GoalProposalCardProps) {
  const [title, setTitle] = useState(initialTitle);
  const [horizon, setHorizon] = useState<Horizon>(initialHorizon);
  const [description, setDescription] = useState(initialDescription ?? "");
  const [targetDate, setTargetDate] = useState(initialTargetDate ?? "");
  const [subtasks, setSubtasks] = useState<string[]>(initialSubtasks);
  const [draft, setDraft] = useState("");

  const trimmedSubtasks = useMemo(
    () => subtasks.map((s) => s.trim()).filter(Boolean),
    [subtasks],
  );

  const canSubmit = title.trim().length > 0;

  const addSubtask = () => {
    const v = draft.trim();
    if (!v) return;
    if (subtasks.includes(v)) {
      setDraft("");
      return;
    }
    setSubtasks([...subtasks, v]);
    setDraft("");
  };

  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface my-3 max-w-lg shadow-soft border border-ink/[0.06] overflow-hidden">
        <header className="flex items-center gap-2 px-5 pt-5 pb-3">
          <span
            aria-hidden
            className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-leaf-soft text-leaf-ink"
          >
            <Target size={14} />
          </span>
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-sm text-ink">Nueva meta</h4>
            <p className="text-xs text-stone">Edita lo que quieras antes de guardar.</p>
          </div>
        </header>

        <div className="px-5 pb-3 flex flex-col gap-3">
          <div>
            <label className="text-[11px] uppercase tracking-wide text-stone font-medium mb-1 block">
              Título
            </label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ej. Ser senior fullstack en 6 meses"
            />
          </div>

          <div>
            <label className="text-[11px] uppercase tracking-wide text-stone font-medium mb-1 block">
              Horizonte
            </label>
            <div className="flex flex-wrap gap-1.5">
              {HORIZONS.map((h) => (
                <button
                  key={h.id}
                  type="button"
                  onClick={() => setHorizon(h.id)}
                  className={cn(
                    "text-xs rounded-tag px-3 py-1.5 border transition-colors duration-180 ease-pirsch focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/20 focus-visible:ring-offset-1",
                    horizon === h.id
                      ? "bg-ink text-canvas border-ink"
                      : "bg-canvas border-ink/15 hover:border-ink/30 text-ink",
                  )}
                  aria-pressed={horizon === h.id}
                >
                  {h.label}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-stone mt-1">
              {HORIZONS.find((h) => h.id === horizon)?.help}
            </p>
          </div>

          <div className="grid grid-cols-[1fr_140px] gap-3 items-start">
            <div>
              <label className="text-[11px] uppercase tracking-wide text-stone font-medium mb-1 block">
                Descripción
              </label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                placeholder="Contexto, motivación…"
              />
            </div>
            <div>
              <label className="text-[11px] uppercase tracking-wide text-stone font-medium mb-1 flex items-center gap-1">
                <Calendar size={11} />
                <span>Fecha objetivo</span>
              </label>
              <Input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] uppercase tracking-wide text-stone font-medium">
                Sub-tareas ({trimmedSubtasks.length})
              </span>
            </div>
            {trimmedSubtasks.length > 0 ? (
              <ul className="flex flex-col gap-1 mb-2">
                {trimmedSubtasks.map((s, i) => (
                  <li
                    key={`${s}-${i}`}
                    className="flex items-center justify-between gap-2 rounded-btn bg-canvas px-3 py-1.5 text-xs text-ink border border-ink/[0.06]"
                  >
                    <span className="truncate">{s}</span>
                    <button
                      type="button"
                      onClick={() => setSubtasks(subtasks.filter((x) => x !== s))}
                      className="text-stone hover:text-ink shrink-0"
                      aria-label={`Quitar ${s}`}
                    >
                      <X size={12} />
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
            <div className="flex items-center gap-2">
              <Input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addSubtask();
                  }
                }}
                placeholder="Añade una sub-tarea y pulsa Enter"
              />
              <Button
                size="sm"
                variant="ghost"
                onClick={addSubtask}
                leadingIcon={<Plus size={14} />}
                disabled={!draft.trim()}
              >
                Añadir
              </Button>
            </div>
          </div>
        </div>

        <footer className="flex items-center gap-2 px-5 py-4 bg-canvas/40 border-t border-ink/[0.05]">
          <Button
            size="sm"
            disabled={!canSubmit}
            loading={pending}
            onClick={() =>
              void onConfirm({
                title: title.trim(),
                horizon,
                description: description.trim() || undefined,
                target_date: targetDate || undefined,
                subtasks: trimmedSubtasks,
              })
            }
          >
            {pending ? "Guardando" : "Guardar meta"}
          </Button>
          <Button size="sm" variant="ghost" onClick={onCancel}>
            Cancelar
          </Button>
          {trimmedSubtasks.length > 0 ? (
            <Badge tone="leaf" size="sm" className="ml-auto">
              {trimmedSubtasks.length} sub-tarea{trimmedSubtasks.length === 1 ? "" : "s"}
            </Badge>
          ) : null}
        </footer>
      </div>
    </ChatMessageMotion>
  );
}
