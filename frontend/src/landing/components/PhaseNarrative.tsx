import { useState, useEffect } from "react";
import { AnimatePresence, motion } from "motion/react";

const PHASES = [
  { word: "Dispersa", desc: "Experiencias en documentos sueltos, perfiles olvidados, notas sin conexión." },
  { word: "Conectada", desc: "Toda tu trayectoria importada en un grafo estructurado y relacional." },
  { word: "Viva", desc: "Tu agente descubre, enriquece y mantiene todo actualizado automáticamente." },
];

export function PhaseNarrative() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((i) => (i + 1) % PHASES.length);
    }, 3200);
    return () => clearInterval(timer);
  }, []);

  const phase = PHASES[index];

  return (
    <section className="py-6 border-b border-ink/5 overflow-hidden">
      <div className="max-w-4xl mx-auto px-6 text-center">
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <span className="text-sm text-stone">Tu trayectoria está</span>
          <span className="relative inline-block min-w-[120px] text-center">
            <AnimatePresence mode="wait">
              <motion.span
                key={phase.word}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.4, ease: [0.2, 0.8, 0.2, 1] }}
                className="inline-block font-display text-lg text-ink"
              >
                {phase.word}
              </motion.span>
            </AnimatePresence>
          </span>
          <span className="text-sm text-stone">—</span>
          <AnimatePresence mode="wait">
            <motion.span
              key={phase.desc}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35 }}
              className="text-sm text-stone/70"
            >
              {phase.desc}
            </motion.span>
          </AnimatePresence>
        </div>
        {/* Progress dots */}
        <div className="flex justify-center gap-1.5 mt-3">
          {PHASES.map((_, i) => (
            <div
              key={i}
              className={`w-1.5 h-1.5 rounded-full transition-colors duration-500 ${
                i === index ? "bg-sunbeam" : "bg-ink/10"
              }`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
