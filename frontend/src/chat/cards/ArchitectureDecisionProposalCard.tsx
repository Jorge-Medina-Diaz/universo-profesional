/**
 * ArchitectureDecisionProposalCard — HITL card to confirm an ADR.
 *
 * Editable: title, context, decision, consequences, status, tags. Returns
 * the payload to the agent via respond() and the coherence engine persists.
 */
import { useState } from "react";
import { Layers, X, Plus } from "lucide-react";
import { Badge, Button, ChatMessageMotion, Input, Textarea, cn } from "@/ui";

type AdrStatus = "proposed" | "accepted" | "superseded" | "rejected";

const STATUSES: { id: AdrStatus; label: string; tone: string }[] = [
  { id: "proposed", label: "Propuesto", tone: "bg-stone/15 text-ink" },
  { id: "accepted", label: "Aceptado", tone: "bg-leaf-soft text-leaf-ink" },
  { id: "superseded", label: "Reemplazado", tone: "bg-amber-100 text-amber-800" },
  { id: "rejected", label: "Rechazado", tone: "bg-rose-100 text-rose-800" },
];

export interface AdrProposalPayload {
  title: string;
  context?: string;
  decision?: string;
  consequences?: string;
  status: AdrStatus;
  tags: string[];
  related_project_id?: string;
}

export interface ArchitectureDecisionProposalCardProps {
  initialTitle: string;
  initialContext?: string;
  initialDecision?: string;
  initialConsequences?: string;
  initialStatus?: AdrStatus;
  initialTags?: string[];
  initialRelatedProjectId?: string;
  pending: boolean;
  onConfirm: (payload: AdrProposalPayload) => void | Promise<void>;
  onCancel: () => void;
}

export function ArchitectureDecisionProposalCard({
  initialTitle,
  initialContext,
  initialDecision,
  initialConsequences,
  initialStatus,
  initialTags,
  initialRelatedProjectId,
  pending,
  onConfirm,
  onCancel,
}: ArchitectureDecisionProposalCardProps) {
  const [title, setTitle] = useState(initialTitle);
  const [context, setContext] = useState(initialContext ?? "");
  const [decision, setDecision] = useState(initialDecision ?? "");
  const [consequences, setConsequences] = useState(initialConsequences ?? "");
  const [status, setStatus] = useState<AdrStatus>(initialStatus ?? "accepted");
  const [tags, setTags] = useState<string[]>(initialTags ?? []);
  const [draft, setDraft] = useState("");

  const canSubmit = title.trim().length > 0;

  const addTag = () => {
    const v = draft.trim();
    if (!v || tags.includes(v)) {
      setDraft("");
      return;
    }
    setTags([...tags, v]);
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
            <Layers size={14} />
          </span>
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-sm text-ink">Decisión arquitectónica</h4>
            <p className="text-xs text-stone">
              ADR: context → decision → consequences. Editable.
            </p>
          </div>
        </header>

        <div className="px-5 pb-3 flex flex-col gap-3">
          <Field label="Título">
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ej. Adoptar event-driven para el sistema de pagos"
            />
          </Field>

          <Field label="Context">
            <Textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              rows={2}
              placeholder="Qué problema o necesidad lo motivó."
            />
          </Field>

          <Field label="Decision">
            <Textarea
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
              rows={2}
              placeholder="Qué se eligió."
            />
          </Field>

          <Field label="Consequences">
            <Textarea
              value={consequences}
              onChange={(e) => setConsequences(e.target.value)}
              rows={2}
              placeholder="Trade-offs aceptados, costes, riesgos."
            />
          </Field>

          <Field label="Status">
            <div className="flex flex-wrap gap-1.5">
              {STATUSES.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setStatus(s.id)}
                  className={cn(
                    "px-2.5 py-1 text-[11px] rounded-full transition-all border",
                    status === s.id
                      ? `${s.tone} border-transparent`
                      : "bg-surface text-stone border-hairline hover:border-ink/[0.2]",
                  )}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </Field>

          <Field label="Tags">
            <div className="flex flex-wrap items-center gap-1">
              {tags.map((t) => (
                <Badge key={t} tone="stone">
                  {t}
                  <button
                    type="button"
                    className="ml-1"
                    aria-label={`Quitar etiqueta ${t}`}
                    onClick={() => setTags(tags.filter((x) => x !== t))}
                  >
                    <X size={10} aria-hidden="true" />
                  </button>
                </Badge>
              ))}
              <div className="flex items-center gap-1">
                <Input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addTag();
                    }
                  }}
                  placeholder="add tag"
                  className="h-7 text-[11px] w-24"
                />
                <button
                  type="button"
                  className="text-stone hover:text-ink"
                  aria-label="Añadir etiqueta"
                  onClick={addTag}
                >
                  <Plus size={12} aria-hidden="true" />
                </button>
              </div>
            </div>
          </Field>

          {initialRelatedProjectId ? (
            <div className="flex items-center gap-2 text-[11px] text-stone">
              <Badge tone="stone">Linked</Badge>
              <span className="truncate">
                proyecto {initialRelatedProjectId.slice(0, 8)}…
              </span>
            </div>
          ) : null}
        </div>

        <footer className="border-t border-ink/[0.06] bg-canvas px-5 py-3 flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onCancel} disabled={pending}>
            Descartar
          </Button>
          <Button
            variant="primary"
            size="sm"
            disabled={!canSubmit || pending}
            onClick={() =>
              onConfirm({
                title: title.trim(),
                context: context.trim() || undefined,
                decision: decision.trim() || undefined,
                consequences: consequences.trim() || undefined,
                status,
                tags,
                related_project_id: initialRelatedProjectId,
              })
            }
          >
            {pending ? "Guardando…" : "Guardar ADR"}
          </Button>
        </footer>
      </div>
    </ChatMessageMotion>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[11px] uppercase tracking-wide text-stone font-medium mb-1 block">
        {label}
      </label>
      {children}
    </div>
  );
}
