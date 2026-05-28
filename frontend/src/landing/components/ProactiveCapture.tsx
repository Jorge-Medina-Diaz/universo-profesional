import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Check, Sparkles, CornerDownLeft } from "lucide-react";
import { SectionHeading } from "./SectionHeading";

type Entity = { label: string; kind: "skill" | "tech" | "exp" | "proj" | "achv" };

interface Script {
  id: string;
  label: string;
  prompt: string; // what the user casually says
  agentIntro: string;
  openQ: string;
  scaleLabel: string;
  options: string[];
  chosen: number;
  userPick: string;
  agentDone: string;
  entities: Entity[];
}

const SCRIPTS: Script[] = [
  {
    id: "swe",
    label: "Ingeniería de software",
    prompt:
      "Esta semana monté un pipeline RAG con pgvector y optimicé las queries con índices parciales.",
    agentIntro: "Buen trabajo. Detecté varias cosas — ¿te hago un par de preguntas para enriquecer tu universo?",
    openQ: "¿Qué problema resolvía ese pipeline?",
    scaleLabel: "Tu nivel con pgvector / embeddings",
    options: ["Básico", "Sólido", "Experto"],
    chosen: 1,
    userPick: "Búsqueda semántica sobre 2M de documentos. Sólido.",
    agentDone: "Hecho. Añadí 3 skills y un proyecto, y los vinculé a tu experiencia actual.",
    entities: [
      { label: "RAG", kind: "skill" },
      { label: "pgvector", kind: "tech" },
      { label: "Query optimization", kind: "skill" },
      { label: "Búsqueda semántica · 2M docs", kind: "proj" },
    ],
  },
  {
    id: "nurse",
    label: "Enfermería",
    prompt: "Hoy lideré una reanimación en urgencias y formé a dos residentes nuevos.",
    agentIntro: "Eso es muy valioso para tu perfil. ¿Me cuentas un poco más?",
    openQ: "¿Con qué frecuencia coordinas el equipo en una urgencia?",
    scaleLabel: "Tu nivel en RCP avanzada (SVA)",
    options: ["En formación", "Competente", "Referente"],
    chosen: 2,
    userPick: "Casi cada turno. Soy referente de SVA en mi unidad.",
    agentDone: "Perfecto. Añadí 2 skills y un logro, vinculados a tu puesto en Urgencias.",
    entities: [
      { label: "RCP avanzada (SVA)", kind: "skill" },
      { label: "Liderazgo en crisis", kind: "skill" },
      { label: "Formación de residentes", kind: "achv" },
    ],
  },
  {
    id: "mkt",
    label: "Marketing",
    prompt: "Lancé una campaña de growth que subió la activación un 18% en un mes.",
    agentIntro: "Resultado cuantificable, justo lo que da fuerza a un CV. ¿Afinamos?",
    openQ: "¿Qué canal movió la aguja?",
    scaleLabel: "Tu nivel con analítica de producto",
    options: ["Básico", "Avanzado", "Experto"],
    chosen: 1,
    userPick: "Lifecycle por email + onboarding. Nivel avanzado.",
    agentDone: "Listo. Añadí 2 skills y un logro con su métrica, vinculados a tu rol actual.",
    entities: [
      { label: "Growth marketing", kind: "skill" },
      { label: "Analítica de producto", kind: "skill" },
      { label: "+18% activación", kind: "achv" },
    ],
  },
];

const KIND_COLOR: Record<Entity["kind"], string> = {
  skill: "#6ece9d",
  tech: "#00d4aa",
  exp: "#ffda6e",
  proj: "#00d4aa",
  achv: "#ffda6e",
};
const KIND_LABEL: Record<Entity["kind"], string> = {
  skill: "Skill",
  tech: "Tecnología",
  exp: "Experiencia",
  proj: "Proyecto",
  achv: "Logro",
};

const EASE = [0.2, 0.8, 0.2, 1] as const;
// beats: 0 user, 1 agent typing→intro, 2 card, 3 user pick, 4 agent done (+entities)
const STEP_DELAYS = [900, 1600, 2200, 1700, 2600];

export function ProactiveCapture() {
  const [tab, setTab] = useState(0);
  const [step, setStep] = useState(0);
  const script = SCRIPTS[tab];
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    setStep(0);
  }, [tab]);

  useEffect(() => {
    const delay = STEP_DELAYS[step] ?? 2500;
    timer.current = setTimeout(() => {
      setStep((s) => (s >= 4 ? 0 : s + 1));
    }, delay);
    return () => clearTimeout(timer.current);
  }, [step, tab]);

  return (
    <section id="como" className="relative py-28 md:py-36">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <SectionHeading
          eyebrow="La magia"
          accent="#00d4aa"
          title={
            <>
              No rellenas formularios.
              <br />
              <span className="cos-dim">Hablas.</span>
            </>
          }
          subtitle="Cuéntale tu semana en una frase. El agente pregunta lo justo —preguntas abiertas, escalas— y tu universo crece solo. Proactivo y natural."
        />

        {/* profession switcher */}
        <div className="mt-12 flex flex-wrap justify-center gap-2">
          {SCRIPTS.map((s, i) => (
            <button
              key={s.id}
              onClick={() => setTab(i)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition-all duration-300 ${
                i === tab
                  ? "bg-[var(--cos-ink)] text-[#0a0a0a]"
                  : "border border-[var(--cos-hairline)] text-[var(--cos-stone)] hover:text-[var(--cos-ink)]"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        <div className="mt-12 grid items-start gap-6 lg:grid-cols-[1.15fr_1fr]">
          {/* Chat */}
          <div className="cos-panel overflow-hidden">
            <div className="flex items-center gap-2 border-b border-[var(--cos-hairline)] px-5 py-3.5">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#00d4aa] opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-[#00d4aa]" />
              </span>
              <span className="text-xs text-[var(--cos-faint)]">Agente · check-in semanal</span>
            </div>

            <div className="flex min-h-[340px] flex-col gap-3 p-5">
              {/* user prompt */}
              <Bubble who="user" show={step >= 0} text={script.prompt} />

              {/* agent intro */}
              {step === 1 ? (
                <Typing />
              ) : (
                <Bubble who="agent" show={step >= 1} text={script.agentIntro} />
              )}

              {/* deep-dive card */}
              <AnimatePresence>
                {step >= 2 && (
                  <motion.div
                    initial={{ opacity: 0, y: 10, scale: 0.97 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 0.35, ease: EASE }}
                    className="cos-panel-raised rounded-2xl p-4"
                  >
                    <div className="mb-1 flex items-center gap-1.5 text-[11px] uppercase tracking-[0.14em] text-[#00d4aa]">
                      <Sparkles size={12} /> Profundizar
                    </div>
                    <p className="mb-3 text-sm text-[var(--cos-ink)]">{script.openQ}</p>
                    <div className="mb-3">
                      <div className="mb-2 text-[11px] text-[var(--cos-faint)]">{script.scaleLabel}</div>
                      <div className="flex flex-wrap gap-2">
                        {script.options.map((opt, i) => {
                          const picked = step >= 3 && i === script.chosen;
                          return (
                            <span
                              key={opt}
                              className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-300 ${
                                picked
                                  ? "border-[#6ece9d]/50 bg-[#6ece9d]/15 text-[#6ece9d]"
                                  : "border-[var(--cos-hairline)] text-[var(--cos-stone)]"
                              }`}
                            >
                              {opt}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* user pick */}
              <Bubble who="user" show={step >= 3} text={script.userPick} />

              {/* agent done */}
              <Bubble who="agent" show={step >= 4} text={script.agentDone} accent />

              {/* composer (static) */}
              <div className="mt-auto flex items-center gap-2 rounded-2xl border border-[var(--cos-hairline)] bg-[rgba(255,255,255,0.02)] px-4 py-2.5">
                <span className="flex-1 text-sm text-[var(--cos-faint)]">Cuéntale a tu agente…</span>
                <span className="grid h-7 w-7 place-items-center rounded-lg bg-[var(--cos-ink)] text-[#0a0a0a]">
                  <CornerDownLeft size={13} />
                </span>
              </div>
            </div>
          </div>

          {/* Blooming entities */}
          <div className="cos-panel relative overflow-hidden p-5 md:p-6">
            <div
              className="pointer-events-none absolute inset-0"
              style={{
                background:
                  "radial-gradient(90% 70% at 80% 0%, rgba(0,212,170,0.08) 0%, transparent 60%)",
              }}
            />
            <div className="relative z-10 mb-4 flex items-center justify-between">
              <span className="text-[11px] uppercase tracking-[0.16em] text-[var(--cos-faint)]">
                Tu universo crece
              </span>
              <span className="text-[11px] text-[#6ece9d]">+{script.entities.length} entidades</span>
            </div>
            <div className="relative z-10 flex flex-col gap-2.5">
              {script.entities.map((ent, i) => (
                <motion.div
                  key={`${script.id}-${ent.label}`}
                  initial={{ opacity: 0, y: 12, scale: 0.95 }}
                  animate={
                    step >= 4
                      ? { opacity: 1, y: 0, scale: 1 }
                      : { opacity: 0, y: 12, scale: 0.95 }
                  }
                  transition={{ delay: step >= 4 ? i * 0.12 : 0, duration: 0.4, ease: EASE }}
                  className="flex items-center gap-3 rounded-xl border border-[var(--cos-hairline)] bg-[rgba(255,255,255,0.025)] px-3.5 py-3"
                >
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{
                      backgroundColor: KIND_COLOR[ent.kind],
                      boxShadow: `0 0 10px 1px ${KIND_COLOR[ent.kind]}`,
                    }}
                  />
                  <span className="flex-1 text-sm text-[var(--cos-ink)]">{ent.label}</span>
                  <span className="text-[10px] uppercase tracking-wide text-[var(--cos-faint)]">
                    {KIND_LABEL[ent.kind]}
                  </span>
                </motion.div>
              ))}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: step >= 4 ? 1 : 0 }}
                transition={{ delay: step >= 4 ? script.entities.length * 0.12 + 0.1 : 0 }}
                className="mt-1 flex items-center gap-2 px-1 text-xs text-[var(--cos-faint)]"
              >
                <Check size={13} className="text-[#6ece9d]" />
                Fusionado sin duplicar y vinculado a tu experiencia.
              </motion.div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Bubble({
  who,
  text,
  show,
  accent,
}: {
  who: "user" | "agent";
  text: string;
  show: boolean;
  accent?: boolean;
}) {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 10, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.32, ease: EASE }}
          className={`flex ${who === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
              who === "user"
                ? "rounded-br-md bg-[var(--cos-ink)] text-[#0a0a0a]"
                : accent
                  ? "rounded-bl-md border border-[#6ece9d]/30 bg-[#6ece9d]/10 text-[var(--cos-ink)]"
                  : "rounded-bl-md border border-[var(--cos-hairline)] bg-[rgba(255,255,255,0.03)] text-[var(--cos-ink)]"
            }`}
          >
            {text}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function Typing() {
  return (
    <div className="flex justify-start">
      <div className="rounded-2xl rounded-bl-md border border-[var(--cos-hairline)] bg-[rgba(255,255,255,0.03)] px-3.5 py-3">
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="h-1.5 w-1.5 rounded-full bg-[var(--cos-stone)]"
              animate={{ y: [0, -4, 0] }}
              transition={{ repeat: Infinity, duration: 0.6, delay: i * 0.15 }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
