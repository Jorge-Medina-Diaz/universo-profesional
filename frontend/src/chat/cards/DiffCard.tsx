/**
 * Renders the result of a coherence upsert when the engine MERGED an entry.
 *
 * Shows old vs new for every changed field. The user confirmed the proposal
 * already — this is the "what just happened" feedback. Toast-like, floats
 * over the chat bottom-right.
 */
import { CheckCircle2, GitMerge, Lightbulb, MinusCircle } from "lucide-react";
import { Badge, ChatMessageMotion } from "@/ui";

interface DiffRow {
  field: string;
  old: unknown;
  new: unknown;
}

export interface DiffCardProps {
  title: string;
  diffs: DiffRow[];
  status: "created" | "merged" | "noop" | "suggested";
}

export function DiffCard({ title, diffs, status }: DiffCardProps) {
  if (status === "created") {
    return (
      <ChatMessageMotion>
        <div className="rounded-card bg-surface p-5 max-w-md shadow-lift border border-ink/[0.06]">
          <div className="flex items-start gap-3">
            <span className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-leaf-soft text-leaf-ink shrink-0">
              <CheckCircle2 size={18} />
            </span>
            <div className="min-w-0">
              <Badge tone="leaf" size="sm" className="mb-1.5">
                Creado
              </Badge>
              <h4 className="font-medium text-sm text-ink leading-tight truncate">{title}</h4>
              <p className="text-xs text-stone mt-1">Añadido a tu universo como entrada nueva.</p>
            </div>
          </div>
        </div>
      </ChatMessageMotion>
    );
  }
  if (status === "noop") {
    return (
      <ChatMessageMotion>
        <div className="rounded-card bg-surface p-5 max-w-md shadow-soft border border-ink/[0.06]">
          <div className="flex items-start gap-3">
            <span className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-black/5 text-stone shrink-0">
              <MinusCircle size={18} />
            </span>
            <div className="min-w-0">
              <Badge tone="stone" size="sm" className="mb-1.5">
                Sin cambios
              </Badge>
              <h4 className="font-medium text-sm text-ink leading-tight truncate">{title}</h4>
              <p className="text-xs text-stone mt-1">Ya estaba registrado así.</p>
            </div>
          </div>
        </div>
      </ChatMessageMotion>
    );
  }
  if (status === "suggested") {
    return (
      <ChatMessageMotion>
        <div className="rounded-card bg-sunbeam-soft p-5 max-w-md shadow-soft border border-sunbeam/40">
          <div className="flex items-start gap-3">
            <span className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-sunbeam text-sunbeam-ink shrink-0">
              <Lightbulb size={18} />
            </span>
            <div className="min-w-0">
              <Badge tone="sunbeam" size="sm" className="mb-1.5">
                Necesita revisión
              </Badge>
              <h4 className="font-medium text-sm text-ink leading-tight">{title}</h4>
              <p className="text-xs text-sunbeam-ink mt-1">
                Hay ambigüedad — la añadí como sugerencia. Revísala en el panel del universo.
              </p>
            </div>
          </div>
        </div>
      </ChatMessageMotion>
    );
  }
  // merged
  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface p-5 max-w-md shadow-soft border border-ink/[0.06]">
        <div className="flex items-start gap-3 mb-3">
          <span className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-leaf-soft text-leaf-ink shrink-0">
            <GitMerge size={18} />
          </span>
          <div className="min-w-0">
            <Badge tone="leaf" size="sm" className="mb-1.5">
              Fusionado
            </Badge>
            <h4 className="font-medium text-sm text-ink leading-tight">{title}</h4>
          </div>
        </div>
        <ul className="text-xs space-y-1.5 border-t border-ink/5 pt-3">
          {diffs.map((d, i) => (
            <li key={`${d.field}-${i}`} className="grid grid-cols-[90px_1fr_auto_1fr] items-baseline gap-2">
              <span className="text-stone font-medium capitalize truncate" title={d.field}>
                {d.field.replace(/_/g, " ")}
              </span>
              <span className="text-stone line-through truncate" title={String(d.old)}>
                {formatValue(d.old)}
              </span>
              <span className="text-stone">→</span>
              <span className="text-ink font-medium truncate" title={String(d.new)}>
                {formatValue(d.new)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </ChatMessageMotion>
  );
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (Array.isArray(v)) return v.join(", ");
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}
