import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { FileText, FileType2 } from "lucide-react";
import { SectionHeading } from "./SectionHeading";

const PHASES = [
  { id: "paste", label: "Pegas la oferta", detail: "Backend Engineer · plataforma de datos" },
  { id: "parse", label: "Analiza", detail: "Detecta 8 skills clave + seniority" },
  { id: "retrieve", label: "Recupera de tu corpus", detail: "RAG híbrido sobre tu universo real" },
  { id: "generate", label: "Genera", detail: "Alinea tus logros con el lenguaje ATS" },
  { id: "download", label: "Descarga", detail: "PDF, DOCX y JSON Resume" },
];

const EASE = [0.2, 0.8, 0.2, 1] as const;

export function CvGenerationDemo() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setPhase((p) => (p + 1) % PHASES.length), 3000);
    return () => clearInterval(interval);
  }, []);

  const current = PHASES[phase];

  return (
    <section className="relative py-28 md:py-36">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <SectionHeading
          eyebrow="El resultado"
          accent="#ffda6e"
          title={
            <>
              Un documento para
              <br />
              <span className="cos-dim">cada oportunidad.</span>
            </>
          }
          subtitle="Nada genérico ni alucinado. Cada CV y carta se construye sobre tu corpus real y se alinea con la oferta, listo para los filtros ATS."
        />

        <div className="mx-auto mt-16 grid max-w-5xl items-center gap-10 lg:grid-cols-2 lg:gap-12">
          {/* Pipeline */}
          <div className="flex flex-col gap-3">
            {PHASES.map((p, i) => {
              const active = i === phase;
              const done = i < phase;
              return (
                <motion.div
                  key={p.id}
                  className={`flex items-center gap-4 rounded-xl border px-5 py-4 transition-all duration-500 ${
                    active
                      ? "border-[var(--cos-hairline-strong)] bg-[rgba(255,255,255,0.04)]"
                      : "border-[var(--cos-hairline)] bg-transparent"
                  }`}
                  animate={{ scale: active ? 1.015 : 1 }}
                >
                  <div
                    className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg text-xs font-bold transition-colors duration-300 ${
                      active
                        ? "bg-[var(--cos-ink)] text-[#0a0a0a]"
                        : done
                          ? "bg-[#6ece9d]/20 text-[#6ece9d]"
                          : "bg-[rgba(255,255,255,0.05)] text-[var(--cos-faint)]"
                    }`}
                  >
                    {done ? "✓" : i + 1}
                  </div>
                  <div className="flex-1">
                    <div
                      className={`text-sm font-medium transition-colors ${
                        active ? "text-[var(--cos-ink)]" : "text-[var(--cos-stone)]"
                      }`}
                    >
                      {p.label}
                    </div>
                    <AnimatePresence>
                      {active && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          className="mt-0.5 text-xs text-[var(--cos-faint)]"
                        >
                          {p.detail}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                  {active && (
                    <motion.div
                      className="h-1.5 w-1.5 rounded-full bg-[#ffda6e]"
                      animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
                      transition={{ repeat: Infinity, duration: 1.2 }}
                    />
                  )}
                </motion.div>
              );
            })}
          </div>

          {/* Document preview */}
          <div className="relative">
            <AnimatePresence mode="wait">
              <motion.div
                key={current.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.4, ease: EASE }}
                className="cos-panel min-h-[260px] p-6 md:p-7"
              >
                {current.id === "paste" && (
                  <div className="space-y-3">
                    <div className="mb-3 text-[11px] uppercase tracking-wider text-[var(--cos-faint)]">
                      Descripción de la oferta
                    </div>
                    <div className="rounded-xl border border-[var(--cos-hairline)] bg-[rgba(255,255,255,0.02)] p-4 text-sm leading-relaxed text-[var(--cos-stone)]">
                      "Buscamos un <span className="text-[var(--cos-ink)]">Backend Engineer</span> con
                      experiencia en <span className="text-[var(--cos-ink)]">sistemas distribuidos</span>,{" "}
                      <span className="text-[var(--cos-ink)]">PostgreSQL</span> y pipelines de datos a{" "}
                      <span className="font-medium text-[#ffda6e]">gran escala</span>."
                    </div>
                  </div>
                )}

                {current.id === "parse" && (
                  <div className="space-y-3">
                    <div className="mb-3 text-[11px] uppercase tracking-wider text-[var(--cos-faint)]">
                      Skills detectadas
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {["Sistemas distribuidos", "PostgreSQL", "Pipelines ETL", "Python", "Observabilidad", "Kubernetes", "Inglés C1", "Liderazgo"].map(
                        (tag, i) => (
                          <motion.span
                            key={tag}
                            initial={{ opacity: 0, scale: 0.8 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: i * 0.06 }}
                            className="rounded-full border border-[#ffda6e]/25 bg-[#ffda6e]/10 px-3 py-1.5 text-[11px] text-[#ffda6e]"
                          >
                            {tag}
                          </motion.span>
                        )
                      )}
                    </div>
                  </div>
                )}

                {current.id === "retrieve" && (
                  <div className="space-y-3">
                    <div className="mb-3 text-[11px] uppercase tracking-wider text-[var(--cos-faint)]">
                      Recuperado de tu universo
                    </div>
                    {[
                      { label: "Backend Engineer @ DataCorp", match: 96 },
                      { label: "Pipeline RAG · 2M docs", match: 92 },
                      { label: "Migración a pgvector", match: 88 },
                    ].map((item, i) => (
                      <motion.div
                        key={item.label}
                        className="flex items-center justify-between rounded-lg border border-[var(--cos-hairline)] bg-[rgba(255,255,255,0.02)] p-3"
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.15 }}
                      >
                        <span className="text-xs text-[var(--cos-ink)]">{item.label}</span>
                        <div className="flex items-center gap-2">
                          <div className="h-1 w-16 overflow-hidden rounded-full bg-[rgba(244,241,234,0.1)]">
                            <motion.div
                              className="h-full rounded-full bg-[#6ece9d]"
                              initial={{ width: 0 }}
                              animate={{ width: `${item.match}%` }}
                              transition={{ duration: 0.8, delay: 0.2 + i * 0.15 }}
                            />
                          </div>
                          <span className="w-7 text-right text-[10px] text-[var(--cos-faint)]">
                            {item.match}%
                          </span>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}

                {current.id === "generate" && (
                  <div className="space-y-3">
                    <div className="mb-3 text-[11px] uppercase tracking-wider text-[var(--cos-faint)]">
                      Bullets generados
                    </div>
                    {[
                      "Diseñé un pipeline RAG sobre pgvector que sirve búsqueda semántica a 2M de documentos con <40 ms de latencia",
                      "Reduje el coste de queries un 60% con índices parciales y reescritura del plan de ejecución",
                      "Lideré la migración a una arquitectura de eventos para 3 equipos de producto",
                    ].map((bullet, i) => (
                      <motion.div
                        key={i}
                        className="flex items-start gap-2.5 rounded-lg border border-[var(--cos-hairline)] bg-[rgba(255,255,255,0.02)] p-3"
                        initial={{ opacity: 0, x: -8 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.2 }}
                      >
                        <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-[#6ece9d]" />
                        <span className="text-xs leading-relaxed text-[var(--cos-ink)]">{bullet}</span>
                      </motion.div>
                    ))}
                  </div>
                )}

                {current.id === "download" && (
                  <div className="space-y-4">
                    <div className="mb-3 text-[11px] uppercase tracking-wider text-[var(--cos-faint)]">
                      Documentos listos
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-xl border border-[var(--cos-hairline)] bg-[rgba(255,255,255,0.03)] p-4 text-center">
                        <FileText size={18} className="mx-auto mb-2 text-[#ffda6e]" />
                        <div className="mb-1 text-xs font-medium text-[var(--cos-ink)]">CV.pdf</div>
                        <div className="text-[10px] text-[var(--cos-faint)]">ATS-friendly</div>
                      </div>
                      <div className="rounded-xl border border-[var(--cos-hairline)] bg-[rgba(255,255,255,0.03)] p-4 text-center">
                        <FileType2 size={18} className="mx-auto mb-2 text-[#6ece9d]" />
                        <div className="mb-1 text-xs font-medium text-[var(--cos-ink)]">Carta.docx</div>
                        <div className="text-[10px] text-[var(--cos-faint)]">Editable</div>
                      </div>
                    </div>
                    <div className="text-center text-[11px] text-[var(--cos-faint)]">
                      También en JSON Resume · 28 idiomas
                    </div>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
