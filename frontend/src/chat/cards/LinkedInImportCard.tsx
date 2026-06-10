/**
 * LinkedInImportCard — chat-native import of the official LinkedIn data
 * export (ZIP): explain how to get it → drop → parse → review → commit.
 *
 * Mirrors PdfImportCard's flow, with ONE honest difference: the backend
 * `/linkedin/zip/commit` endpoint commits the WHOLE parsed session (it has no
 * `selection` contract), so the review phase is a transparent preview — the
 * card says explicitly that everything shown will be imported instead of
 * offering checkboxes that would silently do nothing (no-silent-errors).
 *
 * Failures are surfaced inline (banner) + toast — never console-only.
 */
import { useMemo, useState } from "react";
import { AlertTriangle, Check, Info, X } from "lucide-react";
import { integrations } from "@/shared/api-extra";
import { Badge, Button, ChatMessageMotion, DropZone, LinkedInIcon, toast } from "@/ui";

type Item = Record<string, unknown>;
type ParsedZip = Record<string, Item[] | Record<string, unknown>>;

export interface LinkedInImportSummary {
  committed: Record<string, number>;
  total: number;
}

export interface LinkedInImportCardProps {
  /** Short agent-provided reason for proposing the import (optional). */
  reason?: string;
  /** Resolve the agent tool-call with the outcome. */
  onDone: (summary: LinkedInImportSummary) => void;
  onCancel: () => void;
  /** Invalidate universe/graph queries after a successful commit. */
  onCommitted?: () => void;
}

interface SectionCfg {
  /** Matches the ParsedZip key AND the commit summary key. */
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
  { key: "skills", label: "Skills", primary: (it) => str(it.name) || "Skill" },
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
    secondary: (it) => str(it.description),
  },
  { key: "courses", label: "Cursos", primary: (it) => str(it.title) || "Curso", secondary: (it) => str(it.platform) },
  {
    key: "achievements",
    label: "Logros",
    primary: (it) => str(it.title) || "Logro",
    secondary: (it) => str(it.context),
  },
];

const ZIP_STEPS = [
  "En LinkedIn, abre Ajustes y privacidad → Privacidad de datos.",
  "Elige «Obtener una copia de tus datos» y pide el archivo completo.",
  "LinkedIn te enviará un ZIP por email (suele tardar unos minutos). Súbelo aquí.",
];

type Phase = "intro" | "review" | "committing" | "done";

export function LinkedInImportCard({ reason, onDone, onCancel, onCommitted }: LinkedInImportCardProps) {
  const [phase, setPhase] = useState<Phase>("intro");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [parsed, setParsed] = useState<ParsedZip | null>(null);
  const [summary, setSummary] = useState<LinkedInImportSummary | null>(null);

  const sections = useMemo(() => {
    if (!parsed) return [] as { cfg: SectionCfg; rows: Item[] }[];
    return SECTIONS.map((cfg) => ({
      cfg,
      rows: Array.isArray(parsed[cfg.key]) ? (parsed[cfg.key] as Item[]) : [],
    })).filter((s) => s.rows.length > 0);
  }, [parsed]);

  const totalParsed = useMemo(
    () => sections.reduce((n, s) => n + s.rows.length, 0),
    [sections],
  );

  const handleFiles = async (files: File[]) => {
    const f = files[0];
    if (!f) return;
    setBusy(true);
    setError(null);
    try {
      const res = (await integrations.linkedin.parseZip(f)) as {
        session_id?: string;
        parsed?: ParsedZip;
        detail?: string;
      };
      if (!res?.session_id || !res?.parsed) {
        throw new Error(res?.detail || "No pude leer el ZIP. ¿Es el export oficial de LinkedIn?");
      }
      setSessionId(res.session_id);
      setParsed(res.parsed);
      setPhase("review");
    } catch (e) {
      const msg = (e as Error).message;
      setError(msg);
      toast.error("No se pudo leer el export de LinkedIn", msg);
    } finally {
      setBusy(false);
    }
  };

  const commit = async () => {
    if (!sessionId) return;
    setPhase("committing");
    setError(null);
    try {
      const res = (await integrations.linkedin.commitZip(sessionId)) as {
        committed?: Record<string, number>;
      };
      const committed = res?.committed ?? {};
      const total = Object.values(committed).reduce((n, c) => n + (c || 0), 0);
      onCommitted?.();
      const sum = { committed, total };
      setSummary(sum);
      setPhase("done");
      // No silent drops: if fewer landed than were parsed, say so.
      if (total < totalParsed) {
        toast.error(
          "Algunos elementos no se guardaron",
          `${totalParsed - total} de ${totalParsed} no entraron (duplicados o datos incompletos).`,
        );
      } else {
        toast.success(`Importé ${total} ${total === 1 ? "elemento" : "elementos"} de LinkedIn`);
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
              Añadí {summary.total} {summary.total === 1 ? "elemento" : "elementos"} desde LinkedIn
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
            <LinkedInIcon size={18} />
          </span>
          <div className="min-w-0 space-y-1">
            <Badge tone="sunbeam" size="sm">
              Importar · LinkedIn (ZIP)
            </Badge>
            <h4 className="text-base font-medium leading-tight text-ink">
              {phase === "intro" ? "Trae tu perfil de LinkedIn" : "Esto es lo que encontré"}
            </h4>
            <p className="text-xs text-stone">
              {phase === "intro"
                ? reason ||
                  "Sube el export oficial de tus datos y estructuro experiencias, formación, skills, idiomas, certificaciones y proyectos."
                : "Revisa el contenido antes de confirmar. El export se importa completo; después podrás depurar o borrar cualquier elemento desde el chat."}
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-3 flex items-start gap-2 rounded-card border border-danger/30 bg-danger-soft px-3 py-2 text-xs text-danger-ink">
            <AlertTriangle size={14} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {phase === "intro" && (
          <>
            <ol className="mb-4 flex flex-col gap-1.5">
              {ZIP_STEPS.map((step, i) => (
                <li key={step} className="flex items-start gap-2.5 text-xs text-stone">
                  <span
                    aria-hidden
                    className="mt-px grid h-5 w-5 shrink-0 place-items-center rounded-full bg-canvas text-[10px] font-semibold text-ink"
                  >
                    {i + 1}
                  </span>
                  <span className="leading-5">{step}</span>
                </li>
              ))}
            </ol>
            <DropZone
              accept=".zip,application/zip"
              maxBytes={25 * 1024 * 1024}
              loading={busy}
              onFiles={handleFiles}
              onError={(msg) => toast.error("Archivo rechazado", msg)}
              label={busy ? "Leyendo tu export…" : "Arrastra el ZIP de LinkedIn o haz clic"}
              hint="ZIP · hasta 25 MB"
            />
          </>
        )}

        {(phase === "review" || phase === "committing") && (
          <>
            {totalParsed === 0 ? (
              <div className="mb-4 rounded-card border border-hairline bg-canvas px-3 py-4 text-center text-xs text-stone">
                El ZIP no contenía datos importables. Prueba con el export completo de LinkedIn.
              </div>
            ) : (
              <>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-[11px] text-stone">
                    {totalParsed} {totalParsed === 1 ? "elemento detectado" : "elementos detectados"}
                  </span>
                </div>
                <div className="mb-3 flex max-h-[46vh] flex-col gap-4 overflow-y-auto pr-1">
                  {sections.map(({ cfg, rows }) => (
                    <div key={cfg.key}>
                      <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-stone">
                        {cfg.label} · {rows.length}
                      </div>
                      <ul className="flex flex-col gap-1.5">
                        {rows.map((it, idx) => {
                          const sec = cfg.secondary?.(it);
                          return (
                            <li
                              key={`${cfg.key}:${idx}`}
                              className="flex items-center gap-3 rounded-card border border-ink/8 bg-canvas p-2.5"
                            >
                              <span
                                aria-hidden
                                className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-leaf text-ink"
                              >
                                <Check size={13} strokeWidth={2.5} />
                              </span>
                              <div className="min-w-0 flex-1">
                                <div className="truncate text-sm text-ink">{cfg.primary(it)}</div>
                                {sec && <div className="truncate text-[11px] text-stone">{sec}</div>}
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  ))}
                </div>
                <div className="mb-4 flex items-start gap-2 rounded-card border border-hairline bg-canvas px-3 py-2 text-[11px] text-stone">
                  <Info size={13} className="mt-0.5 shrink-0" />
                  <span>
                    El export de LinkedIn se importa completo (sin selección individual). El motor de
                    coherencia fusiona duplicados automáticamente.
                  </span>
                </div>
              </>
            )}
          </>
        )}

        <div className="flex items-center justify-end gap-2">
          {(phase === "review" || phase === "committing") && totalParsed > 0 ? (
            <Button
              size="sm"
              loading={phase === "committing"}
              onClick={commit}
              leadingIcon={phase !== "committing" && <Check size={14} strokeWidth={2.5} />}
            >
              {phase === "committing" ? "Guardando" : `Importar todo (${totalParsed})`}
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
