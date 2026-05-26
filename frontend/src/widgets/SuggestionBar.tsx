import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { Check, X, RefreshCw, Lightbulb, ChevronDown } from "lucide-react";
import { useState } from "react";
import { liveProfile } from "@/shared/api-extra";
import { queryKeys } from "@/shared/queryKeys";
import { Badge, Button, Card, cn } from "@/ui";

interface SuggestionRow {
  id: string;
  kind?: string | null;
  title: string;
  body?: string | null;
  confidence?: number | null;
}

const KIND_LABEL: Record<string, string> = {
  add_skill: "Skill nueva",
  level_up: "Subir nivel",
  add_experience: "Experiencia",
  add_education: "Formación",
  add_project: "Proyecto",
  update: "Actualización",
  missing_field: "Dato faltante",
};

export function SuggestionBar() {
  const qc = useQueryClient();
  const list = useQuery({
    queryKey: queryKeys.suggestions.all,
    queryFn: () => liveProfile.suggestions.list("pending"),
  });
  const regen = useMutation({
    mutationFn: () => liveProfile.suggestions.regenerate(),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.suggestions.all }),
  });
  const act = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "accept" | "reject" }) =>
      liveProfile.suggestions.act(id, action),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.suggestions.all }),
  });

  const items = (list.data ?? []) as SuggestionRow[];
  const [expanded, setExpanded] = useState(false);
  const top = expanded ? items : items.slice(0, 3);
  const grouped = groupByKind(items);

  if (list.isLoading) return null;

  return (
    <Card padding="lg" tone="surface" className="relative overflow-hidden">
      <div
        aria-hidden
        className="absolute -top-16 -right-12 w-48 h-48 rounded-full bg-sunbeam/20 blur-3xl pointer-events-none"
      />
      <header className="relative flex items-center justify-between gap-3 flex-wrap mb-4">
        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-sunbeam-soft text-sunbeam-ink"
          >
            <Lightbulb size={16} />
          </span>
          <div>
            <h2 className="text-heading-sm font-medium tracking-tight">
              Sugerencias para ti
            </h2>
            <p className="text-xs text-stone">
              {items.length === 0
                ? "Sin propuestas pendientes"
                : `${items.length} cosas que podrías mejorar`}
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => regen.mutate()}
          loading={regen.isPending}
          leadingIcon={!regen.isPending && <RefreshCw size={14} />}
        >
          {regen.isPending ? "Recalculando" : "Recalcular"}
        </Button>
      </header>

      {items.length === 0 ? (
        <p className="relative text-sm text-stone">
          Pulsa "Recalcular" para regenerar sugerencias basadas en tu universo actual.
        </p>
      ) : (
        <>
          {grouped.length > 1 && (
            <div className="relative flex flex-wrap gap-1.5 mb-4">
              {grouped.map((g) => (
                <Badge key={g.kind} tone="stone" size="sm">
                  {KIND_LABEL[g.kind] ?? g.kind} · {g.count}
                </Badge>
              ))}
            </div>
          )}

          <ul className="relative flex flex-col gap-2">
            <AnimatePresence initial={false}>
              {top.map((s) => (
                <SuggestionItem
                  key={s.id}
                  suggestion={s}
                  pendingAction={
                    act.isPending && (act.variables as { id?: string })?.id === s.id
                      ? (act.variables as { action: "accept" | "reject" }).action
                      : null
                  }
                  onAccept={() => act.mutate({ id: s.id, action: "accept" })}
                  onReject={() => act.mutate({ id: s.id, action: "reject" })}
                />
              ))}
            </AnimatePresence>
          </ul>

          {items.length > 3 && (
            <div className="relative pt-3 mt-3 border-t border-ink/5">
              <button
                type="button"
                onClick={() => setExpanded((v) => !v)}
                aria-expanded={expanded}
                className="inline-flex items-center gap-1.5 text-xs text-stone hover:text-ink transition-colors"
              >
                <ChevronDown
                  size={12}
                  className={cn("transition-transform duration-180", expanded && "rotate-180")}
                />
                {expanded ? "Ver menos" : `Ver ${items.length - 3} más`}
              </button>
            </div>
          )}
        </>
      )}
    </Card>
  );
}

function SuggestionItem({
  suggestion,
  pendingAction,
  onAccept,
  onReject,
}: {
  suggestion: SuggestionRow;
  pendingAction: "accept" | "reject" | null;
  onAccept: () => void;
  onReject: () => void;
}) {
  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={
        pendingAction === "accept"
          ? { opacity: 0, x: 60, scale: 0.92 }
          : pendingAction === "reject"
            ? { opacity: 0, x: -60, scale: 0.92 }
            : { opacity: 0 }
      }
      transition={{ duration: 0.28, ease: [0.2, 0.8, 0.2, 1] }}
      className="group flex items-start gap-3 rounded-card bg-canvas p-3 border border-ink/[0.05]"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-ink">{suggestion.title}</span>
          {suggestion.kind && (
            <Badge tone="sunbeam" size="sm">
              {KIND_LABEL[suggestion.kind] ?? suggestion.kind}
            </Badge>
          )}
        </div>
        {suggestion.body && (
          <p className="text-xs text-stone mt-1 leading-relaxed">{suggestion.body}</p>
        )}
      </div>
      <div className="flex gap-1 shrink-0">
        <button
          type="button"
          aria-label="Aceptar sugerencia"
          onClick={onAccept}
          disabled={!!pendingAction}
          className={cn(
            "inline-flex items-center justify-center w-8 h-8 rounded-full transition-all duration-180 ease-pirsch",
            "bg-leaf text-ink hover:scale-105 disabled:opacity-60",
          )}
        >
          <Check size={14} strokeWidth={2.5} />
        </button>
        <button
          type="button"
          aria-label="Descartar sugerencia"
          onClick={onReject}
          disabled={!!pendingAction}
          className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-black/[0.04] text-stone hover:text-ink hover:bg-black/[0.08] transition-colors duration-180 ease-pirsch disabled:opacity-60"
        >
          <X size={14} />
        </button>
      </div>
    </motion.li>
  );
}

function groupByKind(items: SuggestionRow[]): { kind: string; count: number }[] {
  const map = new Map<string, number>();
  for (const it of items) {
    const k = it.kind ?? "otra";
    map.set(k, (map.get(k) ?? 0) + 1);
  }
  return Array.from(map.entries()).map(([kind, count]) => ({ kind, count }));
}
