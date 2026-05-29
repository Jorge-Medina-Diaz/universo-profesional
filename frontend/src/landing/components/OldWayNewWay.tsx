import { motion } from "motion/react";
import { FileX2, Sparkles } from "lucide-react";
import { SemanticConstellation, type ConstellationRegion } from "./SemanticConstellation";
import { SectionHeading } from "./SectionHeading";

const SCATTERED = [
  "cv_2021_v7_FINAL_final.pdf",
  "LinkedIn · sin tocar 14 meses",
  "Migración a pgvector · sin documentar",
  "Cert. AWS SAA · perdida en el correo",
  "side-projects en GitHub sin contexto",
  "carta_motivacion_generica.docx",
];

// Compact regioned graph for the "after" — the same semantic kinds,
// arranged to fill a square panel.
const AFTER_REGIONS: ConstellationRegion[] = [
  { id: "exp", label: "Experiencia", color: "#ffda6e", cx: 0.28, cy: 0.26, count: 5, spread: 0.13 },
  { id: "skill", label: "Skills", color: "#6ece9d", cx: 0.72, cy: 0.3, count: 6, spread: 0.14 },
  { id: "proj", label: "Proyectos", color: "#00d4aa", cx: 0.5, cy: 0.7, count: 5, spread: 0.13 },
  { id: "edu", label: "Educación", color: "#6ece9d", cx: 0.2, cy: 0.66, count: 3, spread: 0.1 },
];

const EASE = [0.2, 0.8, 0.2, 1] as const;

export function OldWayNewWay() {
  return (
    <section id="producto" className="relative py-28 md:py-36">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <SectionHeading
          eyebrow="El problema"
          title={
            <>
              Tu trayectoria
              <br />
              <span className="cos-dim">está atrapada.</span>
            </>
          }
          subtitle="Repartida entre un Word que caducó al guardarlo, un LinkedIn que no tocas y certificados perdidos en el correo. Cada cambio de trabajo: reescribir desde cero."
        />

        <div className="mt-16 grid items-stretch gap-6 md:grid-cols-2">
          {/* BEFORE — scattered, decaying */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.6, ease: EASE }}
            className="cos-panel flex flex-col p-6 md:p-7"
          >
            <div className="mb-5 flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-[#e06a5b]" />
              <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--cos-faint)]">
                Antes · disperso
              </span>
            </div>
            <div className="flex flex-1 flex-col gap-2.5">
              {SCATTERED.map((item, i) => (
                <motion.div
                  key={item}
                  initial={{ opacity: 0, x: -12 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.08, ease: EASE }}
                  className="flex items-center gap-3 rounded-xl border border-[var(--cos-hairline)] bg-[var(--cos-fill)] px-4 py-3"
                >
                  <FileX2 size={15} className="shrink-0 text-[#e06a5b]/70" />
                  <span className="text-sm text-[var(--cos-stone)] line-through decoration-[var(--cos-faint)]/50">
                    {item}
                  </span>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* AFTER — living universe */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.6, delay: 0.12, ease: EASE }}
            className="cos-panel-raised relative flex flex-col overflow-hidden rounded-[20px] p-6 md:p-7"
            style={{
              background:
                "radial-gradient(120% 90% at 70% 10%, rgba(110,206,157,0.08) 0%, transparent 55%), var(--cos-panel-raised)",
            }}
          >
            <div className="relative z-10 mb-3 flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#6ece9d] opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-[#6ece9d]" />
              </span>
              <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-[#6ece9d]">
                Después · conectado
              </span>
            </div>
            <div className="relative min-h-[260px] flex-1">
              <SemanticConstellation
                regions={AFTER_REGIONS}
                className="absolute inset-0"
                interactive={false}
                showLabels
                intensity={0.9}
              />
            </div>
            <div className="relative z-10 mt-3 flex items-center justify-between text-[11px] text-[var(--cos-faint)]">
              <span className="inline-flex items-center gap-1.5">
                <Sparkles size={12} className="text-[#ffda6e]" />
                19 entidades · 27 conexiones · vivo
              </span>
              <span className="rounded-full border border-[#6ece9d]/30 bg-[#6ece9d]/10 px-2.5 py-0.5 font-medium text-[#6ece9d]">
                actualizado
              </span>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
