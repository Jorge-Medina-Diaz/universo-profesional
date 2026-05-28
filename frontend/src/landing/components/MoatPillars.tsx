import { motion } from "motion/react";
import { GitMerge, Network, Users, Boxes, Search, ShieldCheck } from "lucide-react";
import { SectionHeading } from "./SectionHeading";

const EASE = [0.2, 0.8, 0.2, 1] as const;

const PILLARS = [
  {
    icon: GitMerge,
    accent: "#6ece9d",
    title: "Coherence Engine",
    desc: "Dices «Python» hoy y «5 años de Python» en seis meses: el sistema fusiona, no duplica. Reglas declarativas por tipo de entidad. Nadie más lo tiene.",
    featured: true,
  },
  {
    icon: Boxes,
    accent: "#ffda6e",
    title: "Universo, no documento",
    desc: "11 tipos de entidad con embeddings, evidencias cruzadas e historial. No editas un archivo: explotas un corpus.",
  },
  {
    icon: Users,
    accent: "#00d4aa",
    title: "28 especialistas",
    desc: "Un coordinador y 28 agentes de dominio. Proponen cambios con tarjetas HITL — nada se escribe sin tu permiso.",
  },
  {
    icon: Network,
    accent: "#6ece9d",
    title: "Grafo + vectores + ESCO",
    desc: "Apache AGE + pgvector en un solo PostgreSQL, anclado a la ontología oficial de la UE: ~3k ocupaciones, ~14k skills.",
  },
  {
    icon: Search,
    accent: "#ffda6e",
    title: "RAG híbrido de 3 carriles",
    desc: "BM25 + similitud densa + PageRank personalizado. Cada CV se construye sobre tu experiencia real, nunca alucinada.",
  },
  {
    icon: ShieldCheck,
    accent: "#00d4aa",
    title: "RGPD nativo · UE",
    desc: "Datos alojados en Europa, cifrado en reposo y tránsito, derecho al olvido. Tus datos son tuyos.",
  },
];

export function MoatPillars() {
  return (
    <section className="relative py-28 md:py-36">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <SectionHeading
          eyebrow="El motor"
          accent="#6ece9d"
          title={
            <>
              Sin magia.
              <br />
              <span className="cos-dim">Solo ingeniería.</span>
            </>
          }
          subtitle="Lo que parece un milagro por fuera es una arquitectura deliberada por dentro — la misma que hace crecer tu universo sin que se rompa."
        />

        <div className="mt-16 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {PILLARS.map((p, i) => (
            <motion.div
              key={p.title}
              initial={{ opacity: 0, y: 22 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.5, delay: (i % 3) * 0.08, ease: EASE }}
              className={`cos-panel group relative overflow-hidden p-6 ${
                p.featured ? "md:col-span-2 lg:col-span-1 lg:row-span-1" : ""
              }`}
            >
              <div
                className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full opacity-0 blur-2xl transition-opacity duration-500 group-hover:opacity-100"
                style={{ background: p.accent }}
              />
              <div
                className="relative mb-4 grid h-11 w-11 place-items-center rounded-xl border border-[var(--cos-hairline)]"
                style={{ background: `${p.accent}14`, color: p.accent }}
              >
                <p.icon size={19} />
              </div>
              <h3 className="relative mb-2 text-base font-semibold text-[var(--cos-ink)]">
                {p.title}
                {p.featured && (
                  <span className="ml-2 rounded-full bg-[#6ece9d]/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[#6ece9d]">
                    exclusivo
                  </span>
                )}
              </h3>
              <p className="relative text-sm leading-relaxed text-[var(--cos-stone)]">{p.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
