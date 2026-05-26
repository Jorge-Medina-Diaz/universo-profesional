import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import { ArrowRight, Sparkles, Upload, Wand2, Plug, CheckCircle2 } from "lucide-react";
import { universe } from "@/shared/api";
import {
  Badge,
  Button,
  Card,
  DropZone,
  Field,
  Input,
  PageHeader,
  Reveal,
  Surface,
  Textarea,
  cn,
  toast,
} from "@/ui";
import { queryKeys } from "@/shared/queryKeys";

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

export function OnboardingPage() {
  const [step, setStep] = useState<Step>("welcome");
  return (
    <Surface width="md" spacing="md">
      <Progress step={step} />

      {step === "welcome" && (
        <Stage
          icon={<Sparkles size={20} />}
          eyebrow={STEP_LABELS.welcome}
          title="¡Bienvenido!"
          body="Vamos a montar tu Universo Profesional en 7 pasos. Menos de 10 minutos."
        >
          <Button size="lg" onClick={() => setStep("import")} trailingIcon={<ArrowRight size={14} />}>
            Empezar
          </Button>
        </Stage>
      )}
      {step === "import" && <ImportStage onNext={() => setStep("headline")} />}
      {step === "headline" && <HeadlineStage onNext={() => setStep("preferences")} />}
      {step === "preferences" && <PreferencesStage onNext={() => setStep("first-cv")} />}
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
          <Button size="lg" onClick={() => (window.location.hash = "#/universe")} trailingIcon={<ArrowRight size={14} />}>
            Ir a mi universo
          </Button>
        </Stage>
      )}
    </Surface>
  );
}

function Progress({ step }: { step: Step }) {
  const idx = STEPS.indexOf(step);
  const pct = ((idx + 1) / STEPS.length) * 100;
  return (
    <Reveal>
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-stone">
          <span>
            Paso {idx + 1} de {STEPS.length}
          </span>
          <span className="font-medium text-ink">{STEP_LABELS[step]}</span>
        </div>
        <div className="relative h-1.5 bg-surface rounded-full overflow-hidden">
          <motion.div
            className="absolute inset-y-0 left-0 bg-leaf rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.5, ease: [0.2, 0.8, 0.2, 1] }}
          />
        </div>
      </div>
    </Reveal>
  );
}

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
    <Reveal>
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
    </Reveal>
  );
}

function ImportStage({ onNext }: { onNext: () => void }) {
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
        </div>
      </div>
    </Stage>
  );
}

function HeadlineStage({ onNext }: { onNext: () => void }) {
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
          <Button variant="ghost" onClick={onNext}>
            Saltar
          </Button>
        </div>
      </div>
    </Stage>
  );
}

function PreferencesStage({ onNext }: { onNext: () => void }) {
  return (
    <Stage
      icon={<Sparkles size={20} />}
      eyebrow={STEP_LABELS.preferences}
      title="Preferencias de carrera"
      body="Cuéntanos qué buscas (rol, salario, remoto, perks…) para que el agente adapte mejor cada CV."
    >
      <div className="flex flex-wrap gap-2">
        <Button
          onClick={() => (window.location.hash = "#/preferences")}
          leadingIcon={<Sparkles size={14} />}
        >
          Definir preferencias
        </Button>
        <Button variant="ghost" onClick={onNext} trailingIcon={<ArrowRight size={14} />}>
          Saltar de momento
        </Button>
      </div>
    </Stage>
  );
}
