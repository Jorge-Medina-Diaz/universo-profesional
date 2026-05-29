import { motion } from "motion/react";
import { MessageCircle, BrainCircuit, UserCheck, Network, FileText } from "lucide-react";

const STEPS = [
  { icon: MessageCircle, title: "Conversación", desc: "Hablas con tu agente como con una persona. Nada de formularios." },
  { icon: BrainCircuit, title: "Enriquecimiento", desc: "Cada respuesta se extrae, estructura y vincula a ESCO automáticamente." },
  { icon: UserCheck, title: "Confirmación", desc: "Tú revisas y confirmas. Human-in-the-loop en cada paso." },
  { icon: Network, title: "Grafo vivo", desc: "Tu universo crece orgánicamente: entidades, relaciones y contexto." },
  { icon: FileText, title: "Documentos", desc: "CVs, cartas y dossiers generados a medida para cada oportunidad." },
];

const MEMORY = [
  { label: "Semántica", desc: "Qué sabes y cómo se relaciona" },
  { label: "Procedural", desc: "Cómo prefieres que se hagan las cosas" },
  { label: "Episódica", desc: "Conversaciones y decisiones pasadas" },
  { label: "Trabajo", desc: "Contexto del turno actual" },
];

export function AgentArchitecture() {
  return (
    <section className="py-32 md:py-40 bg-[var(--cos-bg)] overflow-hidden">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-20">
          <h2 className="font-display text-[var(--cos-ink)] text-4xl md:text-6xl leading-[1.05] tracking-tight mb-6">
            Arquitectura que
            <br />
            <span className="text-[var(--cos-stone)]">piensa contigo.</span>
          </h2>
          <p className="text-lg text-[var(--cos-stone)] max-w-md mx-auto">
            28 agentes especialistas, 4 capas de memoria y un motor de coherencia.
          </p>
        </div>

        {/* Flow */}
        <div className="grid md:grid-cols-5 gap-4 mb-20">
          {STEPS.map((step, i) => (
            <motion.div
              key={step.title}
              className="relative"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
            >
              <div className="rounded-xl border border-[var(--cos-hairline)] bg-[var(--cos-panel)] p-5 hover:border-[var(--cos-hairline-strong)] transition-colors duration-300">
                <div className="w-9 h-9 rounded-lg bg-[var(--cos-fill)] border border-[var(--cos-hairline)] flex items-center justify-center text-[var(--cos-stone)] mb-3">
                  <step.icon size={16} />
                </div>
                <h4 className="text-sm font-medium text-[var(--cos-ink)] mb-1.5">{step.title}</h4>
                <p className="text-[11px] text-[var(--cos-stone)] leading-relaxed">{step.desc}</p>
              </div>
              {i < STEPS.length - 1 && (
                <div className="hidden md:flex absolute -right-2 top-1/2 -translate-y-1/2 z-10">
                  <motion.div className="text-[var(--cos-faint)]" animate={{ x: [0, 4, 0] }} transition={{ repeat: Infinity, duration: 1.5, delay: i * 0.2 }}>
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                      <path d="M4 2l6 5-6 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                  </motion.div>
                </div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Memory + Entities */}
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          <motion.div
            className="rounded-2xl border border-[var(--cos-hairline)] bg-[var(--cos-panel)] p-6 md:p-8"
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h3 className="font-display text-xl text-[var(--cos-ink)] mb-2">4 capas de memoria</h3>
            <p className="text-sm text-[var(--cos-stone)] mb-6">El agente mejora contigo sin fine-tuning.</p>
            <div className="space-y-3">
              {MEMORY.map((mem, i) => (
                <motion.div
                  key={mem.label}
                  className="flex items-center gap-3 p-3 rounded-xl bg-[var(--cos-fill)] border border-[var(--cos-hairline)]"
                  initial={{ opacity: 0, y: 8 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.1 + i * 0.08 }}
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-[var(--cos-nova)] shrink-0" />
                  <div>
                    <div className="text-xs font-medium text-[var(--cos-ink)]">{mem.label}</div>
                    <div className="text-[11px] text-[var(--cos-stone)]">{mem.desc}</div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          <motion.div
            className="rounded-2xl border border-[var(--cos-hairline)] bg-[var(--cos-panel)] p-6 md:p-8"
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h3 className="font-display text-xl text-[var(--cos-ink)] mb-2">Todo tipo de entidad</h3>
            <p className="text-sm text-[var(--cos-stone)] mb-6">Cada faceta de tu trayectoria tiene su lugar.</p>
            <div className="flex flex-wrap gap-2">
              {[
                { label: "Experiencias", color: "#ffda6e" },
                { label: "Educación", color: "#00d4aa" },
                { label: "Proyectos", color: "#00d4aa" },
                { label: "Skills", color: "#6ece9d" },
                { label: "Certificaciones", color: "#ffda6e" },
                { label: "Idiomas", color: "#00d4aa" },
              ].map((ent, i) => (
                <motion.div
                  key={ent.label}
                  className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--cos-fill)] border border-[var(--cos-hairline)]"
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.06 }}
                >
                  <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: ent.color }} />
                  <span className="text-xs text-[var(--cos-stone)]">{ent.label}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
