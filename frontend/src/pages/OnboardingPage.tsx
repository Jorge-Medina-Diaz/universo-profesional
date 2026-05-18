import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { universe } from "@/shared/api";

const STEPS = ["welcome", "import", "headline", "preferences", "first-cv", "mcp", "done"] as const;
type Step = (typeof STEPS)[number];

export function OnboardingPage() {
  const [step, setStep] = useState<Step>("welcome");
  return (
    <div className="max-w-2xl mx-auto py-12 px-4">
      <Progress step={step} />
      {step === "welcome" && (
        <Stage title="¡Bienvenido!" body="Vamos a montar tu Universo Profesional en 7 pasos. <10 minutos.">
          <button className="btn-primary" onClick={() => setStep("import")}>Empezar</button>
        </Stage>
      )}
      {step === "import" && <ImportStage onNext={() => setStep("headline")} />}
      {step === "headline" && <HeadlineStage onNext={() => setStep("preferences")} />}
      {step === "preferences" && <PreferencesStage onNext={() => setStep("first-cv")} />}
      {step === "first-cv" && (
        <Stage title="Tu primer CV" body="Vamos a generarlo con una oferta de muestra.">
          <a className="btn-primary" href="#/cv/new">Generar mi primer CV →</a>
          <button className="btn-secondary ml-2" onClick={() => setStep("mcp")}>Saltar</button>
        </Stage>
      )}
      {step === "mcp" && (
        <Stage title="Conecta tu agente IA" body="Si usas Claude Code, Codex o Cursor, accede a tu universo desde el editor.">
          <a className="btn-primary" href="#/mcp">Ver instrucciones</a>
          <button className="btn-secondary ml-2" onClick={() => setStep("done")}>Finalizar</button>
        </Stage>
      )}
      {step === "done" && (
        <Stage title="¡Listo!" body="Tu universo está creado. Edítalo en cualquier momento.">
          <a className="btn-primary" href="#/universe">Ir a Mi Universo</a>
        </Stage>
      )}
    </div>
  );
}

function Progress({ step }: { step: Step }) {
  const idx = STEPS.indexOf(step);
  return (
    <div className="flex gap-1 mb-8">
      {STEPS.map((s, i) => (
        <div
          key={s}
          className={`flex-1 h-1 rounded ${i <= idx ? "bg-brand-500" : "bg-gray-200"}`}
        />
      ))}
    </div>
  );
}

function Stage({ title, body, children }: { title: string; body: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="text-gray-600">{body}</p>
      <div className="pt-4 flex flex-wrap">{children}</div>
    </div>
  );
}

function ImportStage({ onNext }: { onNext: () => void }) {
  const qc = useQueryClient();
  const upload = useMutation({
    mutationFn: (f: File) => universe.importLinkedIn(f),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["universe"] }),
  });
  return (
    <Stage
      title="Importar datos"
      body="Sube tu export ZIP de LinkedIn (Get a copy of your data) o empieza de cero."
    >
      <input
        type="file"
        accept=".zip"
        className="block mb-3"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) upload.mutate(f);
        }}
      />
      {upload.data && (
        <p className="text-sm text-green-700 mr-3">
          Importado: {upload.data.experiences} experiencias, {upload.data.educations} estudios, {upload.data.skills} skills.
        </p>
      )}
      <button className="btn-primary" onClick={onNext}>Continuar →</button>
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
      title="Tu titular"
      body="Define tu identidad profesional en una frase."
    >
      <div className="w-full space-y-3">
        <input className="input" placeholder="ej. Senior Backend Engineer · Python · MCP" value={headline} onChange={(e) => setHeadline(e.target.value)} />
        <textarea rows={3} className="input" placeholder="Resumen profesional (1-2 frases)" value={summary} onChange={(e) => setSummary(e.target.value)} />
        <div className="flex gap-2">
          <button
            className="btn-primary"
            onClick={async () => {
              await save.mutateAsync();
              onNext();
            }}
          >
            Guardar y continuar →
          </button>
          <button className="btn-secondary" onClick={onNext}>Saltar</button>
        </div>
      </div>
    </Stage>
  );
}

function PreferencesStage({ onNext }: { onNext: () => void }) {
  return (
    <Stage
      title="Preferencias de carrera"
      body="Cuéntanos qué buscas para que adaptemos mejor tus CVs."
    >
      <p className="text-sm text-gray-500 mr-3">(omitido en este MVP — disponible en /universe → preferences)</p>
      <button className="btn-primary" onClick={onNext}>Continuar →</button>
    </Stage>
  );
}
