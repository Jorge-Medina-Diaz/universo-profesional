/**
 * Job autopilot — two-phase modal:
 *  Phase 1 ("setup"): pick template + language + tone (with sensible defaults).
 *  Phase 2 ("run"):   1) generate CV, 2) generate cover letter, 3) mark applied.
 *
 * The setup is intentionally lightweight (3 fields) so the autopilot still
 * feels like a single click — power users can override; everyone else hits
 * "Empezar" and gets the defaults.
 */
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { Wand2, Sparkles, Send, X, FileDown, ChevronDown } from "lucide-react";
import { documents, jobs, type JobRow } from "@/shared/api";
import {
  Badge,
  Button,
  Field,
  ProgressSteps,
  cn,
  type ProgressStep,
  toast,
} from "@/ui";

type StepId = "cv" | "cover" | "mark";

interface StepState {
  status: ProgressStep["status"];
  documentId?: string;
}

const STEP_LABELS: Record<StepId, string> = {
  cv: "Generar CV adaptado",
  cover: "Generar carta de presentación",
  mark: "Marcar como aplicada",
};

interface AutopilotPrefs {
  template: string;
  language: "es" | "en";
  tone: string;
}

const PREFS_STORAGE_KEY = "cvs-saas-autopilot-prefs";

function loadStoredPrefs(): AutopilotPrefs {
  try {
    const raw = localStorage.getItem(PREFS_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<AutopilotPrefs>;
      return {
        template: parsed.template ?? "ats-classic",
        language: parsed.language === "en" ? "en" : "es",
        tone: parsed.tone ?? "professional",
      };
    }
  } catch {
    /* ignore */
  }
  return { template: "ats-classic", language: "es", tone: "professional" };
}

export function AutopilotRunner({
  job,
  onClose,
  onComplete,
}: {
  job: JobRow;
  onClose: () => void;
  onComplete: () => void;
}) {
  const [phase, setPhase] = useState<"setup" | "run">("setup");
  const [prefs, setPrefs] = useState<AutopilotPrefs>(() => loadStoredPrefs());

  return (
    <AnimatePresence>
      <motion.div
        key="autopilot"
        role="dialog"
        aria-modal="true"
        aria-label="Autopilot"
        className="fixed inset-0 z-[60] flex items-center justify-center p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <motion.button
          type="button"
          aria-label="Cerrar"
          onClick={() => phase === "setup" && onClose()}
          className="absolute inset-0 bg-ink/35 backdrop-blur-sm cursor-default"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        />
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
          className="relative w-full max-w-md rounded-card bg-canvas shadow-lift border border-ink/8 overflow-hidden"
        >
          <header className="flex items-start justify-between gap-3 px-5 py-4 border-b border-ink/5">
            <div className="flex items-start gap-3">
              <span
                aria-hidden
                className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-leaf-soft text-leaf-ink"
              >
                <Wand2 size={16} />
              </span>
              <div>
                <h2 className="text-heading-sm font-medium tracking-tight">
                  Autopilot
                </h2>
                <p className="text-xs text-stone mt-0.5">
                  {job.title ?? "Oferta"}
                  {job.company_name ? ` · ${job.company_name}` : ""}
                </p>
              </div>
            </div>
            {phase === "setup" && (
              <button
                type="button"
                onClick={onClose}
                aria-label="Cerrar"
                className="w-8 h-8 inline-flex items-center justify-center rounded-full text-stone hover:text-ink hover:bg-black/[0.04] transition-colors"
              >
                <X size={14} />
              </button>
            )}
          </header>

          {phase === "setup" ? (
            <SetupPhase
              prefs={prefs}
              onChange={setPrefs}
              onCancel={onClose}
              onStart={() => {
                try {
                  localStorage.setItem(PREFS_STORAGE_KEY, JSON.stringify(prefs));
                } catch {
                  /* ignore */
                }
                setPhase("run");
              }}
            />
          ) : (
            <RunPhase
              job={job}
              prefs={prefs}
              onClose={onClose}
              onComplete={onComplete}
            />
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

function SetupPhase({
  prefs,
  onChange,
  onStart,
  onCancel,
}: {
  prefs: AutopilotPrefs;
  onChange: (p: AutopilotPrefs) => void;
  onStart: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="px-5 py-4 space-y-4">
      <p className="text-sm text-stone">
        El autopilot generará un CV y una carta de presentación adaptados a esta oferta y la marcará como aplicada.
      </p>
      <div className="grid grid-cols-1 gap-3">
        <Field label="Plantilla del CV">
          {(p) => (
            <Select
              {...p}
              value={prefs.template}
              onChange={(e) => onChange({ ...prefs, template: e.target.value })}
            >
              <option value="ats-classic">ATS clásica — pasa filtros</option>
              <option value="modern">Moderna — 2 columnas + pills</option>
              <option value="minimal">Minimal — serif centrado</option>
            </Select>
          )}
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Idioma">
            {(p) => (
              <Select
                {...p}
                value={prefs.language}
                onChange={(e) =>
                  onChange({ ...prefs, language: e.target.value as "es" | "en" })
                }
              >
                <option value="es">Español</option>
                <option value="en">English</option>
              </Select>
            )}
          </Field>
          <Field label="Tono">
            {(p) => (
              <Select
                {...p}
                value={prefs.tone}
                onChange={(e) => onChange({ ...prefs, tone: e.target.value })}
              >
                <option value="professional">Profesional</option>
                <option value="conversational">Conversacional</option>
              </Select>
            )}
          </Field>
        </div>
      </div>
      <div className="flex items-center justify-end gap-2 pt-2">
        <Button variant="ghost" size="sm" onClick={onCancel}>
          Cancelar
        </Button>
        <Button onClick={onStart} leadingIcon={<Wand2 size={14} />}>
          Empezar
        </Button>
      </div>
      <p className="text-[11px] text-stone">
        Recordaremos estas preferencias para el próximo autopilot.
      </p>
    </div>
  );
}

function RunPhase({
  job,
  prefs,
  onClose,
  onComplete,
}: {
  job: JobRow;
  prefs: AutopilotPrefs;
  onClose: () => void;
  onComplete: () => void;
}) {
  const [states, setStates] = useState<Record<StepId, StepState>>({
    cv: { status: "active" },
    cover: { status: "pending" },
    mark: { status: "pending" },
  });
  const [running, setRunning] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cvDocId, setCvDocId] = useState<string | null>(null);
  const [coverDocId, setCoverDocId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const cv = await documents.generate({
          job_url: job.url ?? undefined,
          job_description: job.description_raw || undefined,
          template: prefs.template,
          language: prefs.language,
          tone: prefs.tone,
          kind: "cv",
        });
        if (cancelled) return;
        setCvDocId(cv.document_id);
        setStates((s) => ({
          ...s,
          cv: { status: "done", documentId: cv.document_id },
          cover: { status: "active" },
        }));

        const cover = await documents.generate({
          job_url: job.url ?? undefined,
          job_description: job.description_raw || undefined,
          template: prefs.template,
          language: prefs.language,
          tone: prefs.tone,
          kind: "cover_letter",
        });
        if (cancelled) return;
        setCoverDocId(cover.document_id);
        setStates((s) => ({
          ...s,
          cover: { status: "done", documentId: cover.document_id },
          mark: { status: "active" },
        }));

        await jobs.patch(job.id, { status: "applied" });
        if (cancelled) return;
        setStates((s) => ({ ...s, mark: { status: "done" } }));
        setRunning(false);
        onComplete();
        toast.success(
          "Autopilot completado",
          "CV + carta generados y oferta marcada como aplicada.",
        );
      } catch (e) {
        if (cancelled) return;
        const msg = (e as Error).message;
        setError(msg);
        setRunning(false);
        setStates((s) => {
          const next = { ...s };
          (["cv", "cover", "mark"] as StepId[]).forEach((id) => {
            if (next[id].status === "active") next[id] = { status: "error" };
          });
          return next;
        });
        toast.error("Autopilot interrumpido", msg);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const steps: ProgressStep[] = (Object.keys(STEP_LABELS) as StepId[]).map((id) => ({
    id,
    label: STEP_LABELS[id],
    status: states[id].status,
  }));

  return (
    <>
      <div className="px-5 py-4">
        <div className="flex items-center justify-end mb-3">
          <Badge tone="stone" size="sm">
            {prefs.template} · {prefs.language.toUpperCase()} · {prefs.tone}
          </Badge>
        </div>
        <ProgressSteps steps={steps} />
        {error && (
          <div className="mt-4 rounded-card bg-danger-soft border border-danger/30 text-danger-ink text-xs px-3 py-2">
            {error}
          </div>
        )}
        {!running && !error && (
          <div className="mt-4 flex flex-wrap gap-2">
            {cvDocId && (
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  window.open(
                    `/api/v1/documents/${cvDocId}/pdf`,
                    "_blank",
                    "noopener,noreferrer",
                  )
                }
                leadingIcon={<FileDown size={12} />}
              >
                CV PDF
              </Button>
            )}
            {coverDocId && (
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  window.open(
                    `/api/v1/documents/${coverDocId}/pdf`,
                    "_blank",
                    "noopener,noreferrer",
                  )
                }
                leadingIcon={<FileDown size={12} />}
              >
                Carta PDF
              </Button>
            )}
            <Button
              size="sm"
              onClick={() => {
                if (cvDocId) {
                  window.location.hash = `#/documents/${cvDocId}`;
                } else {
                  onClose();
                }
              }}
              leadingIcon={<Sparkles size={12} />}
            >
              Ver CV
            </Button>
          </div>
        )}
      </div>

      <footer className="flex items-center justify-between gap-3 px-5 py-3 bg-surface/40 border-t border-ink/5 text-[11px] text-stone">
        <span className="inline-flex items-center gap-1.5">
          <Send size={11} />
          {running ? "En curso…" : error ? "Detenido" : "Completado"}
        </span>
        {!running && (
          <Badge tone={error ? "danger" : "leaf"} size="sm">
            {error ? "Error" : "Aplicada"}
          </Badge>
        )}
      </footer>
    </>
  );
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
}
function Select({ className, children, ...rest }: SelectProps) {
  return (
    <div className="relative">
      <select
        {...rest}
        className={cn(
          "appearance-none block w-full rounded-input bg-black/[0.04] text-ink",
          "px-3 py-2.5 text-sm font-normal transition-colors duration-180 ease-pirsch",
          "border border-transparent focus:outline-none focus:border-ink focus:bg-black/[0.06]",
          "pr-8 cursor-pointer",
          className,
        )}
      >
        {children}
      </select>
      <ChevronDown
        size={14}
        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-stone pointer-events-none"
      />
    </div>
  );
}
