import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import {
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Upload,
  Wand2,
  Plug,
  Plus,
  CheckCircle2,
} from "lucide-react";
import { universe, useAuthStore, type CvParseCandidates } from "@/shared/api";
import {
  Badge,
  Button,
  Card,
  DropZone,
  Field,
  Input,
  PageHeader,
  ProgressSteps,
  type ProgressStep,
  Surface,
  Textarea,
  cn,
  toast,
} from "@/ui";
import { queryKeys } from "@/shared/queryKeys";
import { markOnboardingComplete } from "@/shared/onboarding";

const STORAGE_KEY = "cvs-saas-onboarding-step";

const STEPS = ["welcome", "import", "headline", "skills", "preferences", "first-cv", "mcp", "done"] as const;
type Step = (typeof STEPS)[number];

const STEP_LABELS: Record<Step, string> = {
  welcome: "Bienvenida",
  import: "Importar",
  headline: "Titular",
  skills: "Habilidades",
  preferences: "Preferencias",
  "first-cv": "Tu primer CV",
  mcp: "Agente IA",
  done: "Listo",
};

function readStepFromUrl(): Step | null {
  try {
    const hash = window.location.hash || "#/";
    const q = hash.includes("?") ? hash.split("?")[1] : "";
    const p = new URLSearchParams(q);
    const s = p.get("step") as Step;
    if (STEPS.includes(s)) return s;
  } catch {
    /* ignore */
  }
  return null;
}

function readStepFromStorage(): Step | null {
  try {
    const s = localStorage.getItem(STORAGE_KEY) as Step;
    if (STEPS.includes(s)) return s;
  } catch {
    /* ignore */
  }
  return null;
}

function persistStep(step: Step) {
  try {
    localStorage.setItem(STORAGE_KEY, step);
  } catch {
    /* ignore */
  }
}

function syncUrl(step: Step) {
  const hash = window.location.hash || "#/";
  const base = hash.split("?")[0];
  const next = `${base}?step=${step}`;
  if (hash !== next) {
    window.location.replace(next);
  }
}

export function OnboardingPage() {
  const qc = useQueryClient();
  const userId = useAuthStore((s) => s.userId);
  const [step, setStepState] = useState<Step>(() => {
    return readStepFromUrl() ?? readStepFromStorage() ?? "welcome";
  });

  // Reaching onboarding counts as "seen": from here on the router's gate must
  // not bounce the user back when they leave with an empty universe (e.g. via
  // "Ir a mi universo", "Generar mi primer CV" → /cv/new, or "Ver
  // instrucciones" → /mcp). Without this those buttons looked dead.
  useEffect(() => {
    markOnboardingComplete(userId);
  }, [userId]);

  const summary = useQuery({
    queryKey: queryKeys.universe.summary,
    queryFn: () => universe.summary(),
    staleTime: 60_000,
  });

  const hasData =
    summary.data &&
    (summary.data.counts?.experiences > 0 ||
      summary.data.counts?.educations > 0 ||
      summary.data.counts?.skills > 0);

  const setStep = (next: Step) => {
    setStepState(next);
    persistStep(next);
    syncUrl(next);
  };

  // Initialise URL on first mount so the back button in the browser works.
  useEffect(() => {
    syncUrl(step);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const stepIndex = STEPS.indexOf(step);
  const canGoBack = stepIndex > 0 && step !== "done";

  const progressSteps: ProgressStep[] = STEPS.map((s, i) => ({
    id: s,
    label: STEP_LABELS[s],
    status: i < stepIndex ? "done" : i === stepIndex ? "active" : "pending",
  }));

  const variants = {
    enter: { opacity: 0, x: 24 },
    center: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -24 },
  };

  return (
    <Surface width="md" spacing="md">
      <div className="space-y-6">
        <ProgressSteps steps={progressSteps} orientation="horizontal" />

        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={step}
            variants={variants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.28, ease: [0.2, 0.8, 0.2, 1] }}
          >
            {step === "welcome" && (
              <Stage
                icon={<Sparkles size={20} />}
                eyebrow={STEP_LABELS.welcome}
                title="¡Bienvenido!"
                body="Vamos a montar tu Universo Profesional paso a paso. Menos de 10 minutos."
              >
                <Button
                  size="lg"
                  onClick={() => setStep("import")}
                  trailingIcon={<ArrowRight size={14} />}
                >
                  Empezar
                </Button>
                {hasData && (
                  <Button size="lg" variant="ghost" onClick={() => setStep("done")}>
                    Ya tengo datos — ir al final
                  </Button>
                )}
              </Stage>
            )}

            {step === "import" && (
              <ImportStage
                onNext={() => setStep("headline")}
                onSkip={() => setStep("headline")}
              />
            )}

            {step === "headline" && (
              <HeadlineStage onNext={() => setStep("skills")} onSkip={() => setStep("skills")} />
            )}

            {step === "skills" && (
              <SkillsStage onNext={() => setStep("preferences")} onSkip={() => setStep("preferences")} />
            )}

            {step === "preferences" && (
              <PreferencesStage onNext={() => setStep("first-cv")} onSkip={() => setStep("first-cv")} />
            )}

            {step === "first-cv" && (
              <Stage
                icon={<Wand2 size={20} />}
                eyebrow={STEP_LABELS["first-cv"]}
                title="Tu primer CV"
                body="Vamos a generarlo con una oferta de muestra."
              >
                <Button size="lg" onClick={() => (window.location.hash = "#/cv/new")}>
                  Generar mi primer CV
                </Button>
                <Button size="lg" variant="ghost" onClick={() => setStep("mcp")}>
                  Saltar
                </Button>
              </Stage>
            )}

            {step === "mcp" && (
              <Stage
                icon={<Plug size={20} />}
                eyebrow={STEP_LABELS.mcp}
                title="Conecta tu agente IA"
                body="Si usas Claude Code, Codex o Cursor, accede a tu universo desde el editor."
              >
                <Button size="lg" onClick={() => (window.location.hash = "#/mcp")}>
                  Ver instrucciones
                </Button>
                <Button size="lg" variant="ghost" onClick={() => setStep("done")}>
                  Finalizar
                </Button>
              </Stage>
            )}

            {step === "done" && (
              <Stage
                icon={<CheckCircle2 size={20} />}
                eyebrow={STEP_LABELS.done}
                title="¡Listo!"
                body="Tu universo está creado. Edítalo en cualquier momento."
                tone="leaf"
              >
                <Button
                  size="lg"
                  onClick={async () => {
                    localStorage.removeItem(STORAGE_KEY);
                    // Refetch the universe summary BEFORE navigating so the
                    // Router's onboarding gate re-evaluates with fresh data and
                    // doesn't bounce the user back here on a stale cache.
                    await qc.invalidateQueries({ queryKey: queryKeys.universe.summary });
                    window.location.hash = "#/universe";
                  }}
                  trailingIcon={<ArrowRight size={14} />}
                >
                  Ir a mi universo
                </Button>
              </Stage>
            )}
          </motion.div>
        </AnimatePresence>

        {canGoBack && (
          <div className="flex justify-center">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setStep(STEPS[stepIndex - 1])}
              leadingIcon={<ArrowLeft size={14} />}
            >
              Atrás
            </Button>
          </div>
        )}
      </div>
    </Surface>
  );
}

/* ------------------------------------------------------------------ */
/* Reusable stage card                                                */

function Stage({
  icon,
  eyebrow,
  title,
  body,
  children,
  tone = "sunbeam",
}: {
  icon: React.ReactNode;
  eyebrow: string;
  title: string;
  body: string;
  children: React.ReactNode;
  tone?: "sunbeam" | "leaf";
}) {
  const ringClass =
    tone === "leaf"
      ? "bg-leaf-soft text-leaf-ink"
      : "bg-sunbeam-soft text-sunbeam-ink";
  return (
    <Card padding="lg" className="space-y-5">
      <span
        aria-hidden
        className={cn(
          "inline-flex items-center justify-center w-12 h-12 rounded-full",
          ringClass,
        )}
      >
        {icon}
      </span>
      <PageHeader eyebrow={eyebrow} title={title} subtitle={body} />
      <div className="flex flex-wrap gap-2 pt-2">{children}</div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Import stage                                                       */

function ImportStage({ onNext, onSkip }: { onNext: () => void; onSkip: () => void }) {
  const qc = useQueryClient();
  const [candidates, setCandidates] = useState<CvParseCandidates | null>(null);

  // LinkedIn ZIP → parsed + committed server-side, returns a count summary.
  const linkedin = useMutation({
    mutationFn: (f: File) => universe.importLinkedIn(f),
    onSuccess: (res: {
      experiences?: number;
      educations?: number;
      skills?: number;
      errors?: string[];
    }) => {
      qc.invalidateQueries({ queryKey: queryKeys.universe.all });
      if (res?.errors?.length) {
        toast.error("Importación parcial", res.errors[0]);
      }
    },
    onError: (e: unknown) => toast.error("No se pudo importar el ZIP", (e as Error).message),
  });

  // CV PDF → parsed into candidates for review (NOT committed yet).
  const parsePdf = useMutation({
    mutationFn: (f: File) => universe.importPdf(f),
    onSuccess: (res) => {
      if (res.error) {
        toast.error("No se pudo analizar el CV", res.error);
        return;
      }
      const c = res.candidates;
      const total = c.experience.length + c.education.length + c.skills.length;
      if (total === 0) {
        toast.info("CV analizado", "No encontramos entradas claras. Puedes añadirlas a mano.");
        return;
      }
      setCandidates(c);
    },
    onError: (e: unknown) => toast.error("Error al analizar el CV", (e as Error).message),
  });

  // Commit the reviewed PDF candidates one by one, surfacing any failures.
  const commit = useMutation({
    mutationFn: async (c: CvParseCandidates) => {
      const errors: string[] = [];
      let added = 0;
      const post = async (kind: string, payload: Record<string, unknown>) => {
        try {
          await universe.add(kind, payload);
          added += 1;
        } catch (e) {
          errors.push((e as Error).message);
        }
      };
      for (const e of c.experience) await post("experience", e as Record<string, unknown>);
      for (const e of c.education) await post("education", e as Record<string, unknown>);
      for (const s of c.skills) await post("skill", s as Record<string, unknown>);
      return { added, errors };
    },
    onSuccess: ({ added, errors }) => {
      qc.invalidateQueries({ queryKey: queryKeys.universe.all });
      if (added > 0) toast.success("Importado", `${added} entradas añadidas a tu universo.`);
      if (errors.length) {
        toast.error("Algunas no se añadieron", `${errors.length} fallaron · ${errors[0] ?? ""}`);
      }
      setCandidates(null);
      onNext();
    },
    onError: (e: unknown) => toast.error("No se pudo importar", (e as Error).message),
  });

  const handleFile = (f: File) => {
    const name = f.name.toLowerCase();
    if (name.endsWith(".pdf")) parsePdf.mutate(f);
    else if (name.endsWith(".zip")) linkedin.mutate(f);
    else toast.error("Formato no soportado", "Sube un PDF de tu CV o el ZIP de LinkedIn.");
  };

  // Review screen — confirm extracted CV candidates before committing.
  if (candidates) {
    return (
      <Stage
        icon={<Upload size={20} />}
        eyebrow={STEP_LABELS.import}
        title="Revisa lo que encontramos"
        body="Esto extrajimos de tu CV. Confírmalo para añadirlo a tu universo."
      >
        <div className="w-full space-y-3">
          <div className="flex flex-wrap gap-2">
            <Badge tone="leaf" dot>{candidates.experience.length} experiencias</Badge>
            <Badge tone="sunbeam" dot>{candidates.education.length} estudios</Badge>
            <Badge tone="stone" dot>{candidates.skills.length} skills</Badge>
          </div>
          <Card tone="canvas" bordered padding="sm" className="max-h-56 overflow-auto space-y-1.5 text-sm">
            {candidates.experience.map((e, i) => (
              <div key={`x${i}`}>
                <span className="font-medium text-ink">{e.role}</span>{" "}
                <span className="text-stone">· {e.organization}</span>
              </div>
            ))}
            {candidates.education.map((e, i) => (
              <div key={`e${i}`}>
                <span className="font-medium text-ink">{e.degree || e.field_of_study || "Estudios"}</span>{" "}
                <span className="text-stone">· {e.institution}</span>
              </div>
            ))}
            {candidates.skills.length > 0 && (
              <div className="text-stone pt-1">{candidates.skills.map((s) => s.name).join(" · ")}</div>
            )}
          </Card>
          <div className="flex gap-2">
            <Button
              loading={commit.isPending}
              onClick={() => commit.mutate(candidates)}
              trailingIcon={<ArrowRight size={14} />}
            >
              Importar todo
            </Button>
            <Button variant="ghost" onClick={() => setCandidates(null)} disabled={commit.isPending}>
              Descartar
            </Button>
          </div>
        </div>
      </Stage>
    );
  }

  const busy = parsePdf.isPending || linkedin.isPending;
  return (
    <Stage
      icon={<Upload size={20} />}
      eyebrow={STEP_LABELS.import}
      title="Importar datos"
      body="Sube tu CV en PDF o el export ZIP de LinkedIn. O empieza de cero."
    >
      <div className="w-full space-y-3">
        <DropZone
          accept=".pdf,.zip"
          label={parsePdf.isPending ? "Analizando tu CV…" : "Arrastra tu CV (PDF) o ZIP de LinkedIn, o haz clic"}
          hint="PDF de tu CV · o LinkedIn → Settings → Get a copy of your data"
          loading={busy}
          maxBytes={50 * 1024 * 1024}
          onFiles={(files) => handleFile(files[0])}
          onError={(msg) => toast.error("Archivo no aceptado", msg)}
        />
        {linkedin.data && (
          <Badge tone="leaf" dot>
            Importado: {linkedin.data.experiences} experiencias · {linkedin.data.educations} estudios ·{" "}
            {linkedin.data.skills} skills
          </Badge>
        )}
        <div className="flex gap-2">
          <Button onClick={onNext} trailingIcon={<ArrowRight size={14} />}>
            Continuar
          </Button>
          <Button variant="ghost" onClick={onSkip}>
            Saltar
          </Button>
        </div>
      </div>
    </Stage>
  );
}

/* ------------------------------------------------------------------ */
/* Skills stage                                                       */

function SkillsStage({ onNext, onSkip }: { onNext: () => void; onSkip: () => void }) {
  const qc = useQueryClient();
  const [value, setValue] = useState("");
  const [added, setAdded] = useState<string[]>([]);

  const add = useMutation({
    mutationFn: (name: string) => universe.add("skill", { name, category: "hard" }),
    onSuccess: (_data, name) => {
      setAdded((a) => [...a, name]);
      qc.invalidateQueries({ queryKey: queryKeys.universe.all });
    },
    onError: (e: unknown) => toast.error("No se pudo añadir la habilidad", (e as Error).message),
  });

  const submit = () => {
    const name = value.trim();
    if (!name) return;
    if (added.some((a) => a.toLowerCase() === name.toLowerCase())) {
      setValue("");
      return;
    }
    add.mutate(name);
    setValue("");
  };

  return (
    <Stage
      icon={<Sparkles size={20} />}
      eyebrow={STEP_LABELS.skills}
      title="Tus habilidades"
      body="Añade tus skills clave. Pulsa Enter (o el botón) tras cada una — se guardan al instante."
    >
      <div className="w-full space-y-3">
        <div className="flex gap-2">
          <Input
            placeholder="ej. Python, Liderazgo, Figma…"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                submit();
              }
            }}
          />
          <Button onClick={submit} loading={add.isPending} leadingIcon={<Plus size={14} />}>
            Añadir
          </Button>
        </div>
        {added.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {added.map((s) => (
              <Badge key={s} tone="leaf">
                {s}
              </Badge>
            ))}
          </div>
        )}
        <div className="flex gap-2 pt-1">
          <Button onClick={onNext} trailingIcon={<ArrowRight size={14} />}>
            Continuar
          </Button>
          <Button variant="ghost" onClick={onSkip}>
            Saltar
          </Button>
        </div>
      </div>
    </Stage>
  );
}

/* ------------------------------------------------------------------ */
/* Headline stage                                                     */

function HeadlineStage({ onNext, onSkip }: { onNext: () => void; onSkip: () => void }) {
  const [headline, setHeadline] = useState("");
  const [summary, setSummary] = useState("");
  const save = useMutation({
    mutationFn: () => universe.patchHeader({ headline, summary }),
  });
  return (
    <Stage
      icon={<Sparkles size={20} />}
      eyebrow={STEP_LABELS.headline}
      title="Tu titular"
      body="Define tu identidad profesional en una frase."
    >
      <div className="w-full space-y-3">
        <Field label="Titular">
          {(p) => (
            <Input
              {...p}
              placeholder="ej. Senior Backend Engineer · Python · MCP"
              value={headline}
              onChange={(e) => setHeadline(e.target.value)}
            />
          )}
        </Field>
        <Field label="Resumen">
          {(p) => (
            <Textarea
              {...p}
              rows={3}
              placeholder="Resumen profesional (1-2 frases)"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
            />
          )}
        </Field>
        <div className="flex gap-2 pt-1">
          <Button
            loading={save.isPending}
            onClick={async () => {
              await save.mutateAsync();
              onNext();
            }}
            trailingIcon={<ArrowRight size={14} />}
          >
            Guardar y continuar
          </Button>
          <Button variant="ghost" onClick={onSkip}>
            Saltar
          </Button>
        </div>
      </div>
    </Stage>
  );
}

/* ------------------------------------------------------------------ */
/* Preferences stage                                                  */

function PreferencesStage({ onNext, onSkip }: { onNext: () => void; onSkip: () => void }) {
  return (
    <Stage
      icon={<Sparkles size={20} />}
      eyebrow={STEP_LABELS.preferences}
      title="Preferencias de carrera"
      body="Cuéntanos qué buscas (rol, salario, remoto, perks…) para que el agente adapte mejor cada CV."
    >
      <div className="flex flex-wrap gap-2">
        <Button onClick={onNext} leadingIcon={<Sparkles size={14} />}>
          Definir preferencias
        </Button>
        <Button variant="ghost" onClick={onSkip} trailingIcon={<ArrowRight size={14} />}>
          Saltar de momento
        </Button>
      </div>
    </Stage>
  );
}
