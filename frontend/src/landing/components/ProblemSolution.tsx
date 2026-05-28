import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { FileText, AlertTriangle, Clock, Sparkles, Zap, ArrowRight } from "lucide-react";

const PROBLEM_ITEMS = [
  { icon: FileText, label: "CV_2023_v2_FINAL.docx", stale: true },
  { icon: FileText, label: "CV_2024_ingles.docx", stale: true },
  { icon: FileText, label: "CV_producto_corto.docx", stale: true },
  { icon: AlertTriangle, label: "LinkedIn desactualizado", stale: true },
];

const SOLUTION_NODES = [
  { label: "Stripe", type: "exp", color: "bg-sunbeam" },
  { label: "React", type: "skill", color: "bg-leaf" },
  { label: "Stanford", type: "edu", color: "bg-nova" },
  { label: "UX", type: "skill", color: "bg-leaf" },
  { label: "Google", type: "exp", color: "bg-sunbeam" },
  { label: "TypeScript", type: "skill", color: "bg-leaf" },
];

export function ProblemSolution() {
  const [step, setStep] = useState<"problem" | "transition" | "solution">("problem");

  useEffect(() => {
    const t1 = setTimeout(() => setStep("transition"), 2500);
    const t2 = setTimeout(() => setStep("solution"), 3800);
    const t3 = setTimeout(() => setStep("problem"), 7500);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [step]);

  return (
    <section className="py-20 md:py-28 overflow-hidden">
      <div className="max-w-5xl mx-auto px-6">
        <div className="text-center mb-14">
          <span className="eyebrow text-stone/60 mb-3 block">El problema real</span>
          <h2 className="font-display text-heading-lg text-ink">
            Tu carrera está atrapada en documentos muertos
          </h2>
        </div>

        <div className="relative grid md:grid-cols-2 gap-6 items-stretch min-h-[320px]">
          {/* BEFORE: Static CV mess */}
          <AnimatePresence mode="wait">
            {step !== "solution" && (
              <motion.div
                key="before"
                className="relative bg-canvas rounded-2xl border border-red-100 p-6 shadow-soft overflow-hidden"
                initial={{ opacity: 0, x: -40 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -40, scale: 0.95 }}
                transition={{ duration: 0.5 }}
              >
                <div className="flex items-center gap-2 mb-5">
                  <Clock size={14} className="text-red-400" />
                  <span className="text-xs font-medium text-red-400 uppercase tracking-wider">Antes</span>
                </div>

                <div className="space-y-3">
                  {PROBLEM_ITEMS.map((item, i) => (
                    <motion.div
                      key={item.label}
                      className="flex items-center gap-3 p-3 rounded-xl bg-red-50/50 border border-red-100"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.15 }}
                    >
                      <item.icon size={16} className="text-red-400 shrink-0" />
                      <span className="text-sm text-ink/70 line-through decoration-red-300">
                        {item.label}
                      </span>
                      <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-red-100 text-red-600 font-medium">
                        obsoleto
                      </span>
                    </motion.div>
                  ))}
                </div>

                {/* Stale overlay */}
                <motion.div
                  className="absolute inset-0 bg-red-50/10 pointer-events-none"
                  animate={{ opacity: [0.3, 0.5, 0.3] }}
                  transition={{ repeat: Infinity, duration: 3 }}
                />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Transition bolt (center) */}
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-20 hidden md:block">
            <AnimatePresence>
              {step === "transition" && (
                <motion.div
                  className="w-14 h-14 rounded-full bg-sunbeam flex items-center justify-center shadow-glow-sunbeam"
                  initial={{ scale: 0, rotate: -180 }}
                  animate={{ scale: 1, rotate: 0 }}
                  exit={{ scale: 0, rotate: 180 }}
                  transition={{ type: "spring", damping: 12, stiffness: 200 }}
                >
                  <Zap size={24} className="text-ink" />
                </motion.div>
              )}
            </AnimatePresence>
            {step === "solution" && (
              <motion.div
                className="w-10 h-10 rounded-full bg-leaf/20 flex items-center justify-center"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.3 }}
              >
                <ArrowRight size={16} className="text-leaf" />
              </motion.div>
            )}
          </div>

          {/* AFTER: Living universe */}
          <AnimatePresence mode="wait">
            {step !== "problem" && (
              <motion.div
                key="after"
                className="relative bg-canvas rounded-2xl border border-leaf/20 p-6 shadow-soft overflow-hidden"
                initial={{ opacity: 0, x: 40 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 40, scale: 0.95 }}
                transition={{ duration: 0.5 }}
              >
                <div className="flex items-center gap-2 mb-5">
                  <Sparkles size={14} className="text-leaf" />
                  <span className="text-xs font-medium text-leaf uppercase tracking-wider">Después</span>
                </div>

                {/* Living graph */}
                <div className="relative h-48">
                  <svg className="absolute inset-0 w-full h-full pointer-events-none">
                    {SOLUTION_NODES.slice(0, -1).map((_, i) => {
                      const next = SOLUTION_NODES[i + 1];
                      if (!next) return null;
                      return (
                        <motion.line
                          key={i}
                          x1={`${20 + (i % 3) * 30}%`}
                          y1={`${25 + Math.floor(i / 3) * 45}%`}
                          x2={`${20 + ((i + 1) % 3) * 30}%`}
                          y2={`${25 + Math.floor((i + 1) / 3) * 45}%`}
                          stroke="rgba(110,206,157,0.3)"
                          strokeWidth="1.5"
                          initial={{ pathLength: 0 }}
                          animate={{ pathLength: 1 }}
                          transition={{ delay: i * 0.15, duration: 0.5 }}
                        />
                      );
                    })}
                  </svg>

                  {SOLUTION_NODES.map((node, i) => (
                    <motion.div
                      key={node.label}
                      className="absolute flex flex-col items-center"
                      style={{
                        left: `${15 + (i % 3) * 32}%`,
                        top: `${20 + Math.floor(i / 3) * 50}%`,
                      }}
                      initial={{ scale: 0, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ delay: 0.3 + i * 0.12, type: "spring", damping: 10 }}
                    >
                      <div
                        className={`w-4 h-4 rounded-full ${node.color} shadow-sm ring-2 ring-white`}
                      />
                      <span className="text-[10px] text-stone/70 mt-1 whitespace-nowrap bg-white/80 px-1.5 py-0.5 rounded-full">
                        {node.label}
                      </span>
                    </motion.div>
                  ))}

                  {/* Pulse rings */}
                  <motion.div
                    className="absolute left-[15%] top-[20%] w-4 h-4 rounded-full bg-sunbeam/30"
                    animate={{ scale: [1, 2.5, 1], opacity: [0.5, 0, 0.5] }}
                    transition={{ repeat: Infinity, duration: 2.5 }}
                  />
                  <motion.div
                    className="absolute left-[79%] top-[70%] w-4 h-4 rounded-full bg-leaf/30"
                    animate={{ scale: [1, 2.5, 1], opacity: [0.5, 0, 0.5] }}
                    transition={{ repeat: Infinity, duration: 2.5, delay: 1.2 }}
                  />
                </div>

                <div className="flex items-center justify-between mt-2">
                  <span className="text-[10px] text-stone/50">6 entidades • 8 conexiones • vivo</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-leaf-soft text-leaf-ink font-medium">
                    actualizado hace 2 min
                  </span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <motion.p
          className="text-center text-body text-stone max-w-lg mx-auto mt-10"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          Universo Profesional reemplaza documentos estáticos por un{" "}
          <span className="font-display text-ink">grafo de conocimiento vivo</span>{" "}
          que crece, se conecta y evoluciona contigo.
        </motion.p>
      </div>
    </section>
  );
}
