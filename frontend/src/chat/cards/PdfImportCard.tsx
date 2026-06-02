/**
 * PdfImportCard — chat-native CV-PDF import: drop → parse → confidence-aware
 * review → commit, all INSIDE the conversation.
 *
 * Replaces the old `propose_pdf_import` that merely redirected to /connections.
 * The parser already returns a per-item `confidence` (+ `source_page` on
 * experience/education); we surface it as a colour chip, sort the least-certain
 * rows first and offer a "solo lo dudoso" filter so the user fixes the few
 * uncertain things and trusts the rest. Commit goes through the existing
 * /pdf/commit endpoint, which now enqueues graph enrichment so the freshly
 * imported entities arrive already connected in the universe.
 *
 * Failures are surfaced inline (banner) + toast — never console-only.
 */
import { useMemo, useState } from "react";
import { motion } from "motion/react";
import { AlertTriangle, Check, FileStack, X } from "lucide-react";
import { integrations } from "@/shared/api-extra";
import { Badge, Button, ChatMessageMotion, DropZone, cn, toast } from "@/ui";

type Item = Record<string, unknown>;
type ParsedCv = Record<string, Item[] | Record<string, unknown>>;

export interface PdfImportSummary {
  committed: Record<string, number>;
  total: number;
}

export interface PdfImportCardProps {
  /** Resolve the agent tool-call with the outcome. */
  onDone: (summary: PdfImportSummary & { cancelled?: boolean }) => void;
  onCancel: () => void;
  /** Invalidate universe/graph queries after a successful commit. */
  onCommitted?: () => void;
}

interface SectionCfg {
  /** Matches the ParsedCv key AND the commit `selection` key. */
  key: string;
  label: string;
  primary: (it: Item) => string;
  secondary?: (it: Item) => string | undefined;
}

const str = (v: unknown): string | undefined =>
  typeof v === "string" && v.trim() ? v.trim() : undefined;

const SECTIONS: SectionCfg[] = [
  {
    key: "experiences",
    label: "Experiencia",
    primary: (it) => [str(it.role), str(it.organization)].filter(Boolean).join(" @ ") || "Experiencia",
    secondary: (it) =>
      [str(it.start_date), it.is_current ? "actual" : str(it.end_date)].filter(Boolean).join(" – ") || undefined,
  },
  {
    key: "educations",
    label: "Formación",
    primary: (it) =>
      [str(it.degree) || str(it.field_of_study), str(it.institution)].filter(Boolean).join(" · ") || "Formación",
    secondary: (it) => [str(it.start_date), str(it.end_date)].filter(Boolean).join(" – ") || undefined,
  },
  { key: "skills", label: "Skills", primary: (it) => str(it.name) || "Skill", secondary: (it) => str(it.level) },
  {
    key: "languages",
    label: "Idiomas",
    primary: (it) => [str(it.name), str(it.level)].filter(Boolean).join(" · ") || "Idioma",
  },
  {
    key: "certifications",
    label: "Certificaciones",
    primary: (it) => [str(it.name), str(it.issuer)].filter(Boolean).join(" · ") || "Certificación",
    secondary: (it) => str(it.issued_on),
  },
  {
    key: "projects",
    label: "Proyectos",
    primary: (it) => str(it.name) || "Proyecto",
    secondary: (it) =>
      Array.isArray(it.tech_stack) ? (it.tech_stack as string[]).slice(0, 4).join(" · ") : str(it.description),
  },
  { key: "achievements", label: "Logros", primary: (it) => str(it.title) || "Logro" },
];

/** Map a 0–1 confidence to a colour chip. */
function confidenceChip(c: number): { tone: "leaf" | "sunbeam" | "danger"; label: string } {
  if (c >= 0.8) return { tone: "leaf", label: "Alta" };
  if (c >= 0.6) return { tone: "sunbeam", label: "Media" };
  return { tone: "danger", label: "Revisar" };
}

type Phase = "upload" | "review" | "committing" | "done";

export function PdfImportCard({ onDone, onCancel, onCommitted }: PdfImportCardProps) {
  const [phase, setPhase] = useState<Phase>("upload");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [parsed, setParsed] = useState<ParsedCv | null>(null);
  // Excluded rows keyed by `${sectionKey}:${originalIndex}` (default = included).
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [onlyUncertain, setOnlyUncertain] = useState(false);
  const [summary, setSummary] = useState<PdfImportSummary | null>(null);

  const sections = useMemo(() => {
    if (!parsed) return [] as { cfg: SectionCfg; rows: { it: Item; idx: number; conf: number }[] }[];
    return SECTIONS.map((cfg) => {
      const arr = Array.isArray(parsed[cfg.key]) ? (parsed[cfg.key] as Item[]) : [];
      const rows = arr.map((it, idx) => ({
        it,
        idx,
        conf: typeof it.confidence === "number" ? (it.confidence as number) : 0.8,
      }));
      // Least-certain first so the user fixes problem rows before trusting the rest.
      rows.sort((a, b) => a.conf - b.conf);
      return { cfg, rows };
    }).filter((s) => s.rows.length > 0);
  }, [parsed]);

  const counts = useMemo(() => {
    let total = 0;
    let selected = 0;
    for (const s of sections)
      for (const r of s.rows) {
        total += 1;
        if (!excluded.has(`${s.cfg.key}:${r.idx}`)) selected += 1;
      }
    return { total, selected };
  }, [sections, excluded]);

  const handleFiles = async (files: File[]) => {
    const f = files[0];
    if (!f) return;
    setBusy(true);
    setError(null);
    try {
      const res = (await integrations.pdf.parse(f)) as { session_id?: string; parsed?: ParsedCv; detail?: string };
      if (!res?.session_id || !res?.parsed) {
        throw new Error(res?.detail || "No pude leer el PDF. Prueba con otro archivo.");
      }
      setSessionId(res.session_id);
      setParsed(res.parsed);
      setPhase("review");
    } catch (e) {
      const msg = (e as Error).message;
      setError(msg);
      toast.error("No se pudo leer el CV", msg);
    } finally {
      setBusy(false);
    }
  };

  const toggle = (key: string, idx: number) =>
    setExcluded((prev) => {
      const next = new Set(prev);
      const k = `${key}:${idx}`;
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return next;
    });

  const commit = async () => {
    if (!sessionId) return;
    setPhase("committing");
    setError(null);
    const selection: Record<string, number[]> = {};
    for (const s of sections) {
      const idxs = s.rows.filter((r) => !excluded.has(`${s.cfg.key}:${r.idx}`)).map((r) => r.idx);
      if (idxs.length) selection[s.cfg.key] = idxs;
    }
    try {
      const res = (await integrations.pdf.commit(sessionId, selection)) as {
        committed?: Record<string, number>;
      };
      const committed = res?.committed ?? {};
      const total = Object.values(committed).reduce((n, c) => n + (c || 0), 0);
      onCommitted?.();
      const sum = { committed, total };
      setSummary(sum);
      setPhase("done");
      // No silent drops: if fewer landed than were selected, say so.
      if (total < counts.selected) {
        toast.error(
          "Algunos elementos no se guardaron",
          `${counts.selected - total} de ${counts.selected} no entraron (revisa duplicados o datos incompletos).`,
        );
      } else {
        toast.success(`Importé ${total} ${total === 1 ? "elemento" : "elementos"} de tu CV`);
      }
      onDone(sum);
    } catch (e) {
      const msg = (e as Error).message;
      setError(msg);
      setPhase("review");
      toast.error("No se pudo importar", msg);
    }
  };

  // --- Done view -----------------------------------------------------------
  if (phase === "done" && summary) {
    const lines = SECTIONS.filter((s) => summary.committed[s.key])
      .map((s) => `${summary.committed[s.key]} ${s.label}`)
      .join(" · ");
    return (
      <ChatMessageMotion>
        <div className="my-3 flex max-w-xl items-start gap-3 rounded-card border border-ink/[0.06] bg-surface p-4 shadow-soft">
          <span aria-hidden className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-leaf text-ink">
            <Check size={16} strokeWidth={2.5} />
          </span>
          <div className="min-w-0">
            <h4 className="text-sm font-medium leading-tight text-ink">
              Añadí {summary.total} {summary.total === 1 ? "elemento" : "elementos"} desde tu CV
            </h4>
            {lines && <p className="mt-0.5 text-xs text-stone">{lines}</p>}
            <p className="mt-1 text-[11px] text-stone/80">Conectando tu universo… aparecerán enlazados en el grafo.</p>
          </div>
        </div>
      </ChatMessageMotion>
    );
  }

  return (
    <ChatMessageMotion>
      <div className="my-3 max-w-xl rounded-card border border-ink/[0.06] bg-surface p-5 shadow-soft">
        <div className="mb-4 flex items-start gap-3">
          <span aria-hidden className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-canvas text-ink">
            <FileStack size={18} />
          </span>
          <div className="min-w-0 space-y-1">
            <Badge tone="sunbeam" size="sm">
              Importar · CV en PDF
            </Badge>
            <h4 className="text-base font-medium leading-tight text-ink">
              {phase === "upload" ? "Sube tu CV y lo estructuro" : "Revisa lo que detecté"}
            </h4>
            <p className="text-xs text-stone">
              {phase === "upload"
                ? "Leo tu PDF y extraigo experiencias, formación, skills y más. Tú confirmas antes de guardar."
                : "Ordené primero lo menos seguro. Quita lo que no quieras; lo guardo todo junto."}
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-3 flex items-start gap-2 rounded-card border border-danger/30 bg-danger-soft px-3 py-2 text-xs text-danger-ink">
            <AlertTriangle size={14} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {phase === "upload" && (
          <DropZone
            accept="application/pdf"
            maxBytes={10 * 1024 * 1024}
            loading={busy}
            onFiles={handleFiles}
            onError={(msg) => toast.error("Archivo rechazado", msg)}
            label={busy ? "Leyendo tu CV…" : "Arrastra tu CV o haz clic"}
            hint="PDF · hasta 10 MB"
          />
        )}

        {(phase === "review" || phase === "committing") && (
          <>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[11px] text-stone">
                {counts.selected} de {counts.total} seleccionados
              </span>
              <button
                type="button"
                onClick={() => setOnlyUncertain((v) => !v)}
                aria-pressed={onlyUncertain}
                className={cn(
                  "rounded-full border px-2 py-0.5 text-[11px] transition-colors",
                  onlyUncertain
                    ? "border-ink/20 bg-ink/[0.04] text-ink"
                    : "border-hairline text-stone hover:text-ink",
                )}
              >
                Solo lo dudoso
              </button>
            </div>

            <div className="mb-4 flex max-h-[46vh] flex-col gap-4 overflow-y-auto pr-1">
              {sections.map(({ cfg, rows }) => {
                const visible = onlyUncertain ? rows.filter((r) => r.conf < 0.8) : rows;
                if (!visible.length) return null;
                return (
                  <div key={cfg.key}>
                    <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-stone">
                      {cfg.label}
                    </div>
                    <ul className="flex flex-col gap-1.5">
                      {visible.map((r) => {
                        const k = `${cfg.key}:${r.idx}`;
                        const on = !excluded.has(k);
                        const sec = cfg.secondary?.(r.it);
                        const page = typeof r.it.source_page === "number" ? (r.it.source_page as number) : null;
                        const chip = confidenceChip(r.conf);
                        return (
                          <motion.li
                            key={k}
                            layout
                            transition={{ duration: 0.18, ease: [0.2, 0.8, 0.2, 1] }}
                            className={cn(
                              "flex items-center gap-3 rounded-card border p-2.5 transition-colors",
                              on ? "border-ink/8 bg-canvas" : "border-dashed border-ink/15 bg-canvas/40 opacity-55",
                            )}
                          >
                            <button
                              type="button"
                              onClick={() => toggle(cfg.key, r.idx)}
                              aria-pressed={on}
                              aria-label={on ? "Quitar" : "Incluir"}
                              disabled={phase === "committing"}
                              className={cn(
                                "grid h-6 w-6 shrink-0 place-items-center rounded-full transition-all",
                                on ? "bg-leaf text-ink" : "border border-ink/15 text-stone hover:border-ink/40",
                              )}
                            >
                              {on ? <Check size={13} strokeWidth={2.5} /> : <X size={11} />}
                            </button>
                            <div className="min-w-0 flex-1">
                              <div className="truncate text-sm text-ink">{cfg.primary(r.it)}</div>
                              {(sec || page) && (
                                <div className="truncate text-[11px] text-stone">
                                  {sec}
                                  {sec && page ? " · " : ""}
                                  {page ? `pág. ${page}` : ""}
                                </div>
                              )}
                            </div>
                            <Badge tone={chip.tone} size="sm">
                              {chip.label}
                            </Badge>
                          </motion.li>
                        );
                      })}
                    </ul>
                  </div>
                );
              })}
            </div>
          </>
        )}

        <div className="flex items-center justify-end gap-2">
          {phase === "review" || phase === "committing" ? (
            <Button
              size="sm"
              loading={phase === "committing"}
              disabled={counts.selected === 0 && phase !== "committing"}
              onClick={commit}
              leadingIcon={phase !== "committing" && <Check size={14} strokeWidth={2.5} />}
            >
              {phase === "committing" ? "Guardando" : `Añadir ${counts.selected || ""}`.trim()}
            </Button>
          ) : null}
          <Button
            size="sm"
            variant="ghost"
            disabled={busy || phase === "committing"}
            onClick={onCancel}
            leadingIcon={<X size={14} />}
          >
            Cancelar
          </Button>
        </div>
      </div>
    </ChatMessageMotion>
  );
}
