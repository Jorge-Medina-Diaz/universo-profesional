import { useState } from "react";
import { motion } from "motion/react";
import { Target, TrendingUp, Check, Circle, CircleDot } from "lucide-react";
import { SectionHeading } from "./SectionHeading";

type Severity = "alta" | "media" | "baja";
type MilestoneState = "done" | "active" | "next";

interface Track {
  id: string;
  label: string;
  goal: string;
  completeness: number;
  gaps: { skill: string; severity: Severity }[];
  milestones: { text: string; state: MilestoneState }[];
}

const TRACKS: Track[] = [
  {
    id: "swe",
    label: "Ingeniería de software",
    goal: "Staff Engineer",
    completeness: 78,
    gaps: [
      { skill: "Diseño de sistemas a escala", severity: "alta" },
      { skill: "Mentoría / liderazgo técnico", severity: "media" },
      { skill: "Visibilidad cross-team", severity: "media" },
    ],
    milestones: [
      { text: "Dominar RAG + pgvector en producción", state: "done" },
      { text: "Liderar un proyecto entre equipos", state: "active" },
      { text: "Publicar un ADR de arquitectura clave", state: "next" },
      { text: "Mentorizar a 2 ingenieros junior", state: "next" },
    ],
  },
  {
    id: "nurse",
    label: "Enfermería",
    goal: "Supervisora de Unidad",
    completeness: 71,
    gaps: [
      { skill: "Gestión de equipos de enfermería", severity: "alta" },
      { skill: "Indicadores de calidad asistencial", severity: "media" },
      { skill: "Inglés médico C1", severity: "baja" },
    ],
    milestones: [
      { text: "Referente de RCP avanzada en la unidad", state: "done" },
      { text: "Coordinar turnos y formación de residentes", state: "active" },
      { text: "Liderar un proyecto de mejora de calidad", state: "next" },
      { text: "Certificación en gestión sanitaria", state: "next" },
    ],
  },
  {
    id: "mkt",
    label: "Marketing",
    goal: "Head of Growth",
    completeness: 74,
    gaps: [
      { skill: "Gestión de P&L de marketing", severity: "alta" },
      { skill: "Liderazgo de equipo multidisciplinar", severity: "media" },
      { skill: "Estrategia de marca", severity: "baja" },
    ],
    milestones: [
      { text: "Campaña de growth con +18% activación", state: "done" },
      { text: "Construir el funnel de lifecycle completo", state: "active" },
      { text: "Definir la estrategia anual de adquisición", state: "next" },
      { text: "Contratar y liderar un equipo de 3", state: "next" },
    ],
  },
];

const SEV_COLOR: Record<Severity, string> = {
  alta: "#e0a35b",
  media: "#6ece9d",
  baja: "#9c988e",
};

const EASE = [0.2, 0.8, 0.2, 1] as const;

export function AuditMilestones() {
  const [tab, setTab] = useState(0);
  const track = TRACKS[tab];
  const circ = 2 * Math.PI * 52;

  return (
    <section className="relative py-28 md:py-36">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <SectionHeading
          eyebrow="Audita y crece"
          accent="#ffda6e"
          title={
            <>
              Audita tu perfil.
              <br />
              <span className="cos-dim">Diseña tu próximo nivel.</span>
            </>
          }
          subtitle="El agente revisa tu universo, detecta lo que te falta para el rol que quieres y lo convierte en hitos accionables para tu carrera."
        />

        <div className="mt-12 flex flex-wrap justify-center gap-2">
          {TRACKS.map((t, i) => (
            <button
              key={t.id}
              onClick={() => setTab(i)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition-all duration-300 ${
                i === tab
                  ? "bg-[var(--cos-ink)] text-[#0a0a0a]"
                  : "border border-[var(--cos-hairline)] text-[var(--cos-stone)] hover:text-[var(--cos-ink)]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="mt-12 grid items-stretch gap-6 lg:grid-cols-2">
          {/* Audit */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.6, ease: EASE }}
            className="cos-panel p-6 md:p-8"
          >
            <div className="mb-6 flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-[var(--cos-faint)]">
              <Target size={13} className="text-[#ffda6e]" /> Auditoría · objetivo:
              <span className="text-[var(--cos-ink)]">{track.goal}</span>
            </div>

            <div className="flex items-center gap-6">
              <div className="relative h-32 w-32 shrink-0">
                <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
                  <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(244,241,234,0.1)" strokeWidth="8" />
                  <motion.circle
                    key={track.id}
                    cx="60"
                    cy="60"
                    r="52"
                    fill="none"
                    stroke="url(#auditGrad)"
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray={circ}
                    initial={{ strokeDashoffset: circ }}
                    whileInView={{ strokeDashoffset: circ * (1 - track.completeness / 100) }}
                    viewport={{ once: true }}
                    transition={{ duration: 1.1, ease: EASE }}
                  />
                  <defs>
                    <linearGradient id="auditGrad" x1="0" y1="0" x2="1" y2="1">
                      <stop offset="0%" stopColor="#ffda6e" />
                      <stop offset="100%" stopColor="#6ece9d" />
                    </linearGradient>
                  </defs>
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="cos-display text-3xl text-[var(--cos-ink)]">{track.completeness}%</span>
                  <span className="text-[10px] text-[var(--cos-faint)]">completo</span>
                </div>
              </div>

              <div className="flex-1">
                <div className="mb-3 text-[11px] uppercase tracking-[0.14em] text-[var(--cos-faint)]">
                  Gaps detectados
                </div>
                <div className="flex flex-col gap-2.5">
                  {track.gaps.map((gap, i) => (
                    <motion.div
                      key={`${track.id}-${gap.skill}`}
                      initial={{ opacity: 0, x: -10 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: 0.2 + i * 0.1, ease: EASE }}
                      className="flex items-center gap-2.5"
                    >
                      <span
                        className="h-2 w-2 shrink-0 rounded-full"
                        style={{ backgroundColor: SEV_COLOR[gap.severity] }}
                      />
                      <span className="flex-1 text-sm text-[var(--cos-ink)]">{gap.skill}</span>
                      <span
                        className="text-[10px] uppercase tracking-wide"
                        style={{ color: SEV_COLOR[gap.severity] }}
                      >
                        {gap.severity}
                      </span>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>

          {/* Milestones */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.6, delay: 0.12, ease: EASE }}
            className="cos-panel p-6 md:p-8"
          >
            <div className="mb-6 flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-[var(--cos-faint)]">
              <TrendingUp size={13} className="text-[#6ece9d]" /> Hitos hacia {track.goal}
            </div>
            <ol className="relative ml-1">
              <span className="absolute bottom-3 left-[9px] top-3 w-px bg-[var(--cos-hairline)]" />
              {track.milestones.map((m, i) => (
                <motion.li
                  key={`${track.id}-${m.text}`}
                  initial={{ opacity: 0, x: 10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.15 + i * 0.1, ease: EASE }}
                  className="relative flex items-start gap-4 pb-5 last:pb-0"
                >
                  <span className="relative z-10 mt-0.5 grid h-[19px] w-[19px] place-items-center rounded-full bg-[var(--cos-bg-2)]">
                    {m.state === "done" ? (
                      <Check size={14} className="text-[#6ece9d]" />
                    ) : m.state === "active" ? (
                      <CircleDot size={15} className="text-[#ffda6e]" />
                    ) : (
                      <Circle size={13} className="text-[var(--cos-faint)]" />
                    )}
                  </span>
                  <div className="pt-px">
                    <span
                      className={`text-sm ${
                        m.state === "next" ? "text-[var(--cos-stone)]" : "text-[var(--cos-ink)]"
                      }`}
                    >
                      {m.text}
                    </span>
                    {m.state === "active" && (
                      <span className="ml-2 rounded-full bg-[#ffda6e]/15 px-2 py-0.5 text-[10px] font-medium text-[#ffda6e]">
                        en curso
                      </span>
                    )}
                  </div>
                </motion.li>
              ))}
            </ol>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
