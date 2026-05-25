/**
 * Batch-review card for an ingestion (CV / LinkedIn / dictated background).
 *
 * Imported content is TRUSTED, so we do NOT drip one confirm card per entity.
 * The agent extracts everything into groups and emits ONE
 * `present_import_review`; this card shows the WHOLE set with every item
 * pre-selected. The user reviews once, deselects anything wrong, and commits
 * them together. Each selected item is persisted through the coherence engine
 * (which dedups/merges), so re-importing is safe.
 *
 * Returns to the agent: `{ committed: { [kind]: count }, total: number }`.
 */
import { useMemo, useState } from "react";
import { motion } from "motion/react";
import { Check, FileStack, X } from "lucide-react";
import { Badge, Button, ChatMessageMotion, cn } from "@/ui";

export interface ImportCommitResult {
  committed: Record<string, number>;
  total: number;
}

export interface ImportItem {
  [field: string]: unknown;
}
export interface ImportGroup {
  kind: string;
  items: ImportItem[];
}

export interface ImportReviewCardProps {
  title?: string;
  intro?: string;
  source?: string;
  groups: ImportGroup[];
  pending: boolean;
  /** Commit the selected groups; resolves with what was persisted. */
  onConfirm: (groups: ImportGroup[]) => Promise<ImportCommitResult>;
  onCancel: () => void;
}

const KIND_LABEL: Record<string, string> = {
  experience: "Experiencia",
  education: "Formación",
  project: "Proyectos",
  skill: "Skills",
  certification: "Certificaciones",
  course: "Cursos",
  language: "Idiomas",
  achievement: "Logros",
  interest: "Intereses",
  artifact: "Artefactos",
};

const str = (v: unknown): string | undefined =>
  typeof v === "string" && v.trim() ? v.trim() : undefined;

/** One-line human summary of an item, per kind. */
function primaryLine(kind: string, it: ImportItem): string {
  switch (kind) {
    case "experience":
      return [str(it.role), str(it.organization)].filter(Boolean).join(" @ ") || "Experiencia";
    case "education":
      return (
        [str(it.degree) || str(it.field_of_study), str(it.institution)]
          .filter(Boolean)
          .join(" · ") || "Formación"
      );
    case "project":
      return str(it.name) || "Proyecto";
    case "skill":
      return str(it.name) || "Skill";
    case "certification":
      return [str(it.name), str(it.issuer)].filter(Boolean).join(" · ") || "Certificación";
    case "course":
      return [str(it.title), str(it.platform)].filter(Boolean).join(" · ") || "Curso";
    case "language":
      return [str(it.name), str(it.level)].filter(Boolean).join(" · ") || "Idioma";
    case "achievement":
      return str(it.title) || "Logro";
    case "interest":
      return str(it.name) || "Interés";
    case "artifact":
      return str(it.title) || "Artefacto";
    default:
      return str(it.name) || str(it.title) || kind;
  }
}

/** Optional dimmer secondary line (dates / level / stack). */
function secondaryLine(kind: string, it: ImportItem): string | undefined {
  if (kind === "experience" || kind === "education") {
    const start = str(it.start_date);
    const end = it.is_current ? "actual" : str(it.end_date);
    return [start, end].filter(Boolean).join(" – ") || undefined;
  }
  if (kind === "skill") return str(it.level) || (it.years ? `${it.years} años` : undefined);
  if (kind === "project") {
    const stack = Array.isArray(it.tech_stack) ? (it.tech_stack as string[]).slice(0, 4) : [];
    return stack.length ? stack.join(" · ") : str(it.role);
  }
  if (kind === "certification") return str(it.issued_on);
  if (kind === "artifact") return str(it.type);
  return undefined;
}

export function ImportReviewCard({
  title = "Revisa lo que importaré",
  intro,
  source,
  groups,
  pending,
  onConfirm,
  onCancel,
}: ImportReviewCardProps) {
  // Flat selection state keyed by group+item so every item can toggle.
  const [sel, setSel] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    groups.forEach((g, gi) => g.items.forEach((_, ii) => (init[`${gi}-${ii}`] = true)));
    return init;
  });
  // Show a terminal success view once committed (the agent flow also resolves).
  const [result, setResult] = useState<ImportCommitResult | null>(null);

  const total = useMemo(
    () => Object.values(sel).filter(Boolean).length,
    [sel],
  );
  const grandTotal = useMemo(
    () => groups.reduce((n, g) => n + g.items.length, 0),
    [groups],
  );

  const toggle = (gi: number, ii: number) =>
    setSel((s) => ({ ...s, [`${gi}-${ii}`]: !s[`${gi}-${ii}`] }));

  const submit = async () => {
    const out: ImportGroup[] = groups
      .map((g, gi) => ({
        kind: g.kind,
        items: g.items.filter((_, ii) => sel[`${gi}-${ii}`]),
      }))
      .filter((g) => g.items.length > 0);
    const res = await onConfirm(out);
    setResult(res);
  };

  // Post-commit success view — replaces the form so the card is terminal.
  if (result) {
    const lines = Object.entries(result.committed)
      .map(([k, n]) => `${n} ${KIND_LABEL[k] ?? k}`)
      .join(" · ");
    return (
      <ChatMessageMotion>
        <div className="rounded-card bg-surface p-4 my-3 max-w-xl shadow-soft border border-ink/[0.06] flex items-start gap-3">
          <span
            aria-hidden
            className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-leaf text-ink shrink-0"
          >
            <Check size={16} strokeWidth={2.5} />
          </span>
          <div className="min-w-0">
            <h4 className="font-medium text-sm text-ink leading-tight">
              Añadí {result.total} {result.total === 1 ? "elemento" : "elementos"} a tu universo
            </h4>
            {lines && <p className="text-xs text-stone mt-0.5">{lines}</p>}
          </div>
        </div>
      </ChatMessageMotion>
    );
  }

  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface p-5 my-3 max-w-xl shadow-soft border border-ink/[0.06]">
        <div className="flex items-start gap-3 mb-4">
          <span
            aria-hidden
            className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-canvas text-ink shrink-0"
          >
            <FileStack size={18} />
          </span>
          <div className="min-w-0 space-y-1">
            <Badge tone="sunbeam" size="sm">
              {source ? `Importar · ${source}` : "Importar · revisión"}
            </Badge>
            <h4 className="font-medium text-base text-ink leading-tight">{title}</h4>
            <p className="text-xs text-stone">
              {intro ?? `${grandTotal} elementos detectados. Revisa y quita lo que no quieras; lo guardo todo junto.`}
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-4 mb-4 max-h-[46vh] overflow-y-auto pr-1">
          {groups.map((g, gi) => {
            if (!g.items.length) return null;
            const groupSel = g.items.filter((_, ii) => sel[`${gi}-${ii}`]).length;
            return (
              <div key={`${g.kind}-${gi}`}>
                <div className="flex items-baseline justify-between mb-1.5">
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-stone">
                    {KIND_LABEL[g.kind] ?? g.kind}
                  </span>
                  <span className="text-[11px] text-stone/80">
                    {groupSel}/{g.items.length}
                  </span>
                </div>
                <ul className="flex flex-col gap-1.5">
                  {g.items.map((it, ii) => {
                    const on = sel[`${gi}-${ii}`];
                    const sec = secondaryLine(g.kind, it);
                    return (
                      <motion.li
                        key={`${gi}-${ii}`}
                        layout
                        transition={{ duration: 0.18, ease: [0.2, 0.8, 0.2, 1] }}
                        className={cn(
                          "flex items-center gap-3 rounded-card p-2.5 border transition-colors duration-150 ease-pirsch",
                          on
                            ? "bg-canvas border-ink/8"
                            : "bg-canvas/40 border-dashed border-ink/15 opacity-55",
                        )}
                      >
                        <button
                          type="button"
                          onClick={() => toggle(gi, ii)}
                          aria-pressed={on}
                          aria-label={on ? "Quitar" : "Incluir"}
                          className={cn(
                            "shrink-0 w-6 h-6 rounded-full grid place-items-center transition-all duration-150 ease-pirsch",
                            on
                              ? "bg-leaf text-ink"
                              : "border border-ink/15 text-stone hover:border-ink/40",
                          )}
                        >
                          {on ? <Check size={13} strokeWidth={2.5} /> : <X size={11} />}
                        </button>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-ink truncate">
                            {primaryLine(g.kind, it)}
                          </div>
                          {sec && (
                            <div className="text-[11px] text-stone truncate">{sec}</div>
                          )}
                        </div>
                      </motion.li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>

        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-stone">
            {total === 0 ? "Nada seleccionado" : `${total} de ${grandTotal} elementos`}
          </span>
          <div className="flex gap-2">
            <Button
              size="sm"
              loading={pending}
              disabled={total === 0 && !pending}
              onClick={submit}
              leadingIcon={!pending && <Check size={14} strokeWidth={2.5} />}
            >
              {pending ? "Guardando" : `Añadir ${total || ""}`.trim()}
            </Button>
            <Button size="sm" variant="ghost" disabled={pending} onClick={onCancel}>
              Cancelar
            </Button>
          </div>
        </div>
      </div>
    </ChatMessageMotion>
  );
}
