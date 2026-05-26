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
  CheckCircle2,
} from "lucide-react";
import { universe } from "@/shared/api";
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

const STORAGE_KEY = "cvs-saas-onboarding-step";

const STEPS = ["welcome", "import", "headline", "preferences", "first-cv", "mcp", "done"] as const;
type Step = (typeof STEPS)[number];

const STEP_LABELS: Record<Step, string> = {
  welcome: "Bienvenida",
  import: "Importar",
  headline: "Titular",
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
  const [step, setStepState] = useState<Step>(() => {
    return readStepFromUrl() ?? readStepFromStorage() ?? "welcome";
  });

  const summary = useQuery({
    queryKey: queryKeys.universe.summary,
    queryFn: () => universe.summary(),
    staleTime: 60_000,
  });

  const hasData =
    summary.data &&
    (summary.data.counts.experiences > 0 ||
      summary.data.counts.educations > 0 ||
      summary.data.counts.skills > 0);

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
                body="Vamos a montar tu Universo Profesional en 7 pasos. Menos de 10 minutos."
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
              <HeadlineStage onNext={() => setStep("preferences")} onSkip={() => setStep("preferences")} />
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
                  onClick={() => {
                    localStorage.removeItem(STORAGE_KEY);
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
  const upload = useMutation({
    mutationFn: (f: File) => universe.importLinkedIn(f),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.universe.all }),
  });
  return (
    <Stage
      icon={<Upload size={20} />}
      eyebrow={STEP_LABELS.import}
      title="Importar datos"
      body="Sube tu export ZIP de LinkedIn (Get a copy of your data) o empieza de cero."
    >
      <div className="w-full space-y-3">
        <DropZone
          accept=".zip"
          label="Arrastra tu ZIP de LinkedIn o haz clic"
          hint="Settings → Get a copy of your data en LinkedIn"
          loading={upload.isPending}
          maxBytes={50 * 1024 * 1024}
          onFiles={(files) => upload.mutate(files[0])}
          onError={(msg) => toast.error("Archivo no aceptado", msg)}
        />
        {upload.data && (
          <Badge tone="leaf" dot>
            Importado: {upload.data.experiences} experiencias · {upload.data.educations} estudios ·{" "}
            {upload.data.skills} skills
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

function PreferencesStage({ onSkip }: { onNext: () => void; onSkip: () => void }) {
  return (
    <Stage
      icon={<Sparkles size={20} />}
      eyebrow={STEP_LABELS.preferences}
      title="Preferencias de carrera"
      body="Cuéntanos qué buscas (rol, salario, remoto, perks…) para que el agente adapte mejor cada CV."
    >
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => (window.location.hash = "#/preferences")} leadingIcon={<Sparkles size={14} />}>
          Definir preferencias
        </Button>
        <Button variant="ghost" onClick={onSkip} trailingIcon={<ArrowRight size={14} />}>
          Saltar de momento
        </Button>
      </div>
    </Stage>
  );
}
