import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { FileArchive, Brain, Link2, CheckCircle2 } from "lucide-react";

const PROFESSIONS = [
  {
    name: "Sanidad",
    items: [
      { label: "Enfermera Urgencias @ Hospital General", type: "exp" },
      { label: "Grado Enfermería @ UCM", type: "edu" },
      { label: "Gestión crisis sanitarias", type: "skill" },
      { label: "RCP Avanzada", type: "skill" },
      { label: "Inglés médico C1", type: "lang" },
      { label: "UCI Neonatal @ La Paz", type: "exp" },
    ],
  },
  {
    name: "Arquitectura",
    items: [
      { label: "Arquitecto Senior @ Estudio Sostenible", type: "exp" },
      { label: "Máster Bioclimática @ UPC", type: "edu" },
      { label: "Diseño paramétrico", type: "skill" },
      { label: "Certificación LEED", type: "cert" },
      { label: "Rhinoceros + Grasshopper", type: "skill" },
      { label: "Proyecto Vivienda Passivhaus", type: "proj" },
    ],
  },
  {
    name: "Marketing",
    items: [
      { label: "Directora Marketing @ RetailTech", type: "exp" },
      { label: "MBA @ IE Business School", type: "edu" },
      { label: "Growth Hacking", type: "skill" },
      { label: "Analytics avanzado", type: "skill" },
      { label: "Francés negocios B2", type: "lang" },
      { label: "Liderazgo equipos cross-funcionales", type: "skill" },
    ],
  },
];

const STEPS = [
  { id: "upload", label: "Importas tu perfil", icon: FileArchive },
  { id: "parse", label: "El agente extrae todo", icon: Brain },
  { id: "match", label: "Conecta con ESCO", icon: Link2 },
  { id: "grow", label: "Tu universo crece", icon: CheckCircle2 },
];

export function UniverseNutritionDemo() {
  const [profIdx, setProfIdx] = useState(0);
  const [step, setStep] = useState(0);

  const prof = PROFESSIONS[profIdx];

  useEffect(() => {
    const interval = setInterval(() => {
      setStep((s) => {
        const next = (s + 1) % STEPS.length;
        if (next === 0) setProfIdx((p) => (p + 1) % PROFESSIONS.length);
        return next;
      });
    }, 2800);
    return () => clearInterval(interval);
  }, []);

  const stepId = STEPS[step].id;
  const colorFor = (t: string) => {
    if (t === "exp") return "bg-[#ffda6e]";
    if (t === "skill") return "bg-[#6ece9d]";
    if (t === "cert") return "bg-[#ffda6e]";
    if (t === "lang") return "bg-[#00d4aa]";
    if (t === "proj") return "bg-[#00d4aa]";
    return "bg-[#00d4aa]";
  };

  return (
    <section className="py-32 md:py-40 bg-[var(--cos-bg)] overflow-hidden">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="font-display text-[var(--cos-ink)] text-4xl md:text-6xl leading-[1.05] tracking-tight mb-6">
            Tu perfil se
            <br />
            <span className="text-[var(--cos-stone)]">construye solo.</span>
          </h2>
          <p className="text-lg text-[var(--cos-stone)] max-w-md mx-auto">
            Importa una vez. El agente descubre, conecta y enriquece todo automáticamente.
          </p>
        </div>

        {/* Profession picker */}
        <div className="flex justify-center gap-2 mb-12">
          {PROFESSIONS.map((p, i) => (
            <button
              key={p.name}
              onClick={() => { setProfIdx(i); setStep(0); }}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ${
                i === profIdx
                  ? "bg-[var(--cos-ink)] text-[var(--cos-on-ink)]"
                  : "text-[var(--cos-stone)] hover:text-[var(--cos-ink)] hover:bg-[var(--cos-fill)]"
              }`}
            >
              {p.name}
            </button>
          ))}
        </div>

        <div className="grid md:grid-cols-2 gap-10 max-w-4xl mx-auto">
          {/* Steps */}
          <div className="space-y-2">
            {STEPS.map((s, i) => {
              const active = i === step;
              const done = i < step;
              return (
                <motion.div
                  key={s.id}
                  className={`flex items-center gap-4 px-5 py-4 rounded-xl border transition-colors duration-500 ${
                    active
                      ? "bg-[var(--cos-fill-strong)] border-[var(--cos-hairline-strong)]"
                      : done
                      ? "bg-[var(--cos-fill)] border-[var(--cos-hairline)]"
                      : "bg-transparent border-[var(--cos-hairline)]"
                  }`}
                  animate={{ scale: active ? 1.01 : 1 }}
                >
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center transition-colors duration-500 ${
                      active
                        ? "bg-[var(--cos-ink)] text-[var(--cos-on-ink)]"
                        : done
                        ? "bg-[var(--cos-leaf)]/20 text-[#4a9e6f]"
                        : "bg-[var(--cos-fill)] text-[var(--cos-stone)]"
                    }`}
                  >
                    {done ? <CheckCircle2 size={16} /> : <s.icon size={16} />}
                  </div>
                  <span className={`text-sm font-medium transition-colors ${active ? "text-[var(--cos-ink)]" : done ? "text-[var(--cos-stone)]" : "text-[var(--cos-faint)]"}`}>
                    {s.label}
                  </span>
                  {active && (
                    <motion.div
                      className="ml-auto w-1.5 h-1.5 rounded-full bg-[#ffda6e]"
                      animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
                      transition={{ repeat: Infinity, duration: 1.2 }}
                    />
                  )}
                </motion.div>
              );
            })}

            <div className="pt-2">
              <div className="h-1 bg-[var(--cos-track)] rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-[#ffda6e] to-[#6ece9d] rounded-full"
                  animate={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>
          </div>

          {/* Visual stage */}
          <div className="relative min-h-[300px] rounded-2xl border border-[var(--cos-hairline)] bg-[var(--cos-panel)] overflow-hidden p-5">
            <AnimatePresence mode="wait">
              {stepId === "upload" && (
                <motion.div key="upload" className="absolute inset-0 flex flex-col items-center justify-center p-6" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <motion.div className="w-14 h-16 rounded-lg bg-[#ffda6e]/5 border-2 border-dashed border-[#ffda6e]/20 flex items-center justify-center mb-3" animate={{ y: [0, -6, 0] }} transition={{ repeat: Infinity, duration: 2 }}>
                    <FileArchive size={22} className="text-[#d4a832]" />
                  </motion.div>
                  <span className="text-sm font-medium text-[var(--cos-stone)]">LinkedIn_Export.zip</span>
                  <span className="text-xs text-[var(--cos-faint)] mt-1">2.4 MB</span>
                </motion.div>
              )}

              {stepId === "parse" && (
                <motion.div key="parse" className="absolute inset-0 p-5" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div className="text-[11px] text-[var(--cos-stone)] mb-3 uppercase tracking-wider">Entidades detectadas</div>
                  <div className="space-y-2">
                    {prof.items.map((item, i) => (
                      <motion.div key={item.label} className="flex items-center gap-2.5 p-2.5 rounded-lg bg-[var(--cos-fill)] border border-[var(--cos-hairline)]" initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}>
                        <div className={`w-2 h-2 rounded-full ${colorFor(item.type)}`} />
                        <span className="text-xs text-[var(--cos-ink)]">{item.label}</span>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}

              {stepId === "match" && (
                <motion.div key="match" className="absolute inset-0 p-5" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div className="text-[11px] text-[var(--cos-stone)] mb-3 uppercase tracking-wider">Relaciones descubiertas</div>
                  <div className="space-y-3">
                    {[
                      { a: prof.items[0]?.label.split(" @ ")[0] || "Experiencia", b: prof.items[1]?.label.split(" @ ")[0] || "Educación", rel: "ENABLES" },
                      { a: prof.items[2]?.label || "Skill", b: prof.items[0]?.label.split(" @ ")[0] || "Experiencia", rel: "APPLIES" },
                      { a: prof.items[3]?.label || "Skill", b: prof.items[4]?.label || "Idioma", rel: "REQUIRES" },
                    ].map((pair, i) => (
                      <motion.div key={i} className="flex items-center gap-2" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.2 }}>
                        <span className="text-xs text-[var(--cos-stone)]">{pair.a}</span>
                        <div className="flex-1 h-px bg-[var(--cos-hairline-strong)] relative">
                          <motion.div className="absolute inset-y-0 left-0 bg-[var(--cos-leaf)]/40" initial={{ width: 0 }} animate={{ width: "100%" }} transition={{ delay: 0.3 + i * 0.2, duration: 0.6 }} />
                        </div>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--cos-leaf)]/15 text-[#4a9e6f] font-medium">{pair.rel}</span>
                        <div className="flex-1 h-px bg-[var(--cos-hairline)]" />
                        <span className="text-xs text-[var(--cos-stone)]">{pair.b}</span>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}

              {stepId === "grow" && (
                <motion.div key="grow" className="absolute inset-0 p-5" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div className="text-[11px] text-[var(--cos-stone)] mb-3 uppercase tracking-wider">Tu universo ahora</div>
                  <div className="relative h-full">
                    <svg className="absolute inset-0 w-full h-full pointer-events-none">
                      {[0, 1, 2, 3, 4].map((i) => (
                        <motion.line key={i} x1={`${20 + (i % 3) * 30}%`} y1={`${20 + Math.floor(i / 3) * 40}%`} x2={`${20 + ((i + 1) % 3) * 30}%`} y2={`${20 + Math.floor((i + 1) / 3) * 40}%`} stroke="var(--cos-edge)" strokeWidth="1" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: i * 0.1, duration: 0.4 }} />
                      ))}
                    </svg>
                    {prof.items.slice(0, 6).map((item, i) => (
                      <motion.div key={item.label} className="absolute flex flex-col items-center" style={{ left: `${15 + (i % 3) * 32}%`, top: `${15 + Math.floor(i / 3) * 42}%` }} initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: i * 0.1, type: "spring", damping: 12 }}>
                        <div className={`w-2.5 h-2.5 rounded-full ${colorFor(item.type)} shadow-[0_0_10px_currentColor]`} />
                        <span className="text-[9px] text-[var(--cos-ink)] mt-1 whitespace-nowrap bg-[var(--cos-label-bg)] px-1 rounded shadow-sm">{item.label.split(" @ ")[0]}</span>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
