import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Code2,
  HeartPulse,
  Ruler,
  Megaphone,
  GraduationCap,
  ChefHat,
  ArrowRight,
} from "lucide-react";
import { SemanticConstellation, type ConstellationRegion } from "./SemanticConstellation";
import { SectionHeading } from "./SectionHeading";

function miniRegions(a: string, b: string, c: string): ConstellationRegion[] {
  return [
    { id: "r1", label: "Experiencia", color: a, cx: 0.28, cy: 0.28, count: 4, spread: 0.13 },
    { id: "r2", label: "Skills", color: b, cx: 0.72, cy: 0.32, count: 5, spread: 0.14 },
    { id: "r3", label: "Proyectos", color: c, cx: 0.5, cy: 0.72, count: 4, spread: 0.12 },
  ];
}

const CASES = [
  {
    id: "swe",
    label: "Ingeniería de software",
    icon: Code2,
    accent: "#00d4aa",
    persona: "Backend Engineer",
    pain: "Tu mejor trabajo vive en PRs, incidencias y ramas. Tu CV solo dice «Python, 5 años».",
    captures: ["Stack y arquitecturas", "Proyectos y ADRs", "Incidencias resueltas", "Mentoría", "Certificaciones cloud"],
    generates: ["CV para oferta concreta", "Carta de presentación", "Perfil para entrevistas"],
    regions: miniRegions("#ffda6e", "#6ece9d", "#00d4aa"),
  },
  {
    id: "health",
    label: "Sanidad",
    icon: HeartPulse,
    accent: "#6ece9d",
    persona: "Enfermera de Urgencias",
    pain: "Cada rotación, técnica e idioma se pierde entre convocatorias. Reescribir el CV para cada oposición agota.",
    captures: ["Rotaciones y unidades", "Técnicas y protocolos", "Idiomas médicos", "Formación continua"],
    generates: ["CV para oposición", "Carta de motivación", "Portfolio de rotaciones"],
    regions: miniRegions("#6ece9d", "#00d4aa", "#ffda6e"),
  },
  {
    id: "arch",
    label: "Arquitectura",
    icon: Ruler,
    accent: "#ffda6e",
    persona: "Arquitecto Sostenible",
    pain: "Proyectos, certificaciones y técnicas dispersos. Un concurso pide un dossier impecable y empiezas de cero.",
    captures: ["Proyectos y obras", "Certificaciones (LEED…)", "Herramientas (BIM)", "Premios"],
    generates: ["CV para concurso", "Dossier de proyecto", "Carta de presentación"],
    regions: miniRegions("#ffda6e", "#6ece9d", "#00d4aa"),
  },
  {
    id: "mkt",
    label: "Marketing",
    icon: Megaphone,
    accent: "#00d4aa",
    persona: "Growth Lead",
    pain: "Tus resultados son números —activación, retención, ROI— pero acaban como bullets genéricos sin contexto.",
    captures: ["Campañas y métricas", "Canales dominados", "Herramientas y stack", "Equipos liderados"],
    generates: ["CV ejecutivo", "One-pager de logros", "Carta para dirección"],
    regions: miniRegions("#00d4aa", "#ffda6e", "#6ece9d"),
  },
  {
    id: "edu",
    label: "Educación",
    icon: GraduationCap,
    accent: "#6ece9d",
    persona: "Docente / Investigador",
    pain: "Publicaciones, metodologías y proyectos de innovación viven en mil sitios cuando llega la convocatoria.",
    captures: ["Publicaciones", "Metodologías", "Proyectos de innovación", "Liderazgo de equipos"],
    generates: ["CV para movilidad", "Dossier de innovación", "Carta de intención"],
    regions: miniRegions("#6ece9d", "#ffda6e", "#00d4aa"),
  },
  {
    id: "hosp",
    label: "Hostelería",
    icon: ChefHat,
    accent: "#ffda6e",
    persona: "Jefe de Cocina",
    pain: "Estaciones, técnicas e idiomas que abren puertas internacionales no caben en un CV de una página.",
    captures: ["Estaciones y partidas", "Técnicas culinarias", "Idiomas", "Gestión de equipo"],
    generates: ["CV para hotel internacional", "Dossier de menús", "Carta de recomendación"],
    regions: miniRegions("#ffda6e", "#00d4aa", "#6ece9d"),
  },
];

const EASE = [0.2, 0.8, 0.2, 1] as const;

export function UseCaseConstellation() {
  const [active, setActive] = useState("swe");
  const current = CASES.find((c) => c.id === active)!;

  return (
    <section id="casos" className="relative py-28 md:py-36">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <SectionHeading
          eyebrow="Casos de uso"
          accent="#00d4aa"
          title={
            <>
              Un sistema,
              <br />
              <span className="cos-dim">cualquier profesión.</span>
            </>
          }
          subtitle="Nacido para ingeniería de software, agnóstico por diseño. El agente entiende tu sector y construye el grafo que refleja tu verdadera experiencia."
        />

        <div className="mt-14 grid gap-8 lg:grid-cols-[260px_1fr]">
          {/* Tab rail */}
          <div className="-mx-5 flex gap-2 overflow-x-auto px-5 pb-1 lg:mx-0 lg:flex-col lg:overflow-visible lg:px-0">
            {CASES.map((c) => {
              const Icon = c.icon;
              const on = c.id === active;
              return (
                <button
                  key={c.id}
                  onClick={() => setActive(c.id)}
                  className={`flex shrink-0 items-center gap-3 rounded-2xl border px-4 py-3 text-left text-sm font-medium transition-all duration-300 lg:w-full ${
                    on
                      ? "border-[var(--cos-hairline-strong)] bg-[var(--cos-fill-strong)] text-[var(--cos-ink)]"
                      : "border-[var(--cos-hairline)] text-[var(--cos-stone)] hover:text-[var(--cos-ink)]"
                  }`}
                >
                  <span
                    className="grid h-8 w-8 shrink-0 place-items-center rounded-lg"
                    style={{
                      backgroundColor: on ? `${c.accent}22` : "var(--cos-fill-strong)",
                      color: on ? c.accent : "var(--cos-faint)",
                    }}
                  >
                    <Icon size={16} />
                  </span>
                  <span className="whitespace-nowrap">{c.label}</span>
                </button>
              );
            })}
          </div>

          {/* Panel */}
          <AnimatePresence mode="wait">
            <motion.div
              key={active}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.35, ease: EASE }}
              className="cos-panel grid gap-8 overflow-hidden p-6 md:grid-cols-2 md:p-8"
            >
              <div className="flex flex-col">
                <span
                  className="cos-chip mb-4 self-start"
                  style={{ color: current.accent, borderColor: `${current.accent}40` }}
                >
                  {current.persona}
                </span>
                <p className="cos-display mb-6 text-[clamp(20px,2.4vw,26px)] leading-snug text-[var(--cos-ink)]">
                  {current.pain}
                </p>

                <div className="mb-5">
                  <div className="mb-2.5 text-[11px] uppercase tracking-[0.14em] text-[var(--cos-faint)]">
                    Tu universo captura
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {current.captures.map((cap) => (
                      <span
                        key={cap}
                        className="rounded-full border border-[var(--cos-hairline)] bg-[var(--cos-fill)] px-3 py-1.5 text-xs text-[var(--cos-stone)]"
                      >
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="mb-2.5 text-[11px] uppercase tracking-[0.14em] text-[var(--cos-faint)]">
                    Generas
                  </div>
                  <div className="flex flex-col gap-2">
                    {current.generates.map((g, i) => (
                      <motion.div
                        key={g}
                        initial={{ opacity: 0, x: -8 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.1 + i * 0.08 }}
                        className="flex items-center gap-2.5 text-sm text-[var(--cos-ink)]"
                      >
                        <ArrowRight size={13} style={{ color: current.accent }} />
                        {g}
                      </motion.div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Mini graph */}
              <div
                className="relative min-h-[260px] overflow-hidden rounded-2xl border border-[var(--cos-hairline)]"
                style={{
                  background: `radial-gradient(90% 80% at 60% 20%, ${current.accent}14 0%, transparent 60%)`,
                }}
              >
                <SemanticConstellation
                  key={active}
                  regions={current.regions}
                  className="absolute inset-0"
                  interactive={false}
                  showLabels
                  intensity={0.85}
                />
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}
