import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ArrowRight, Sparkles } from "lucide-react";
import { SemanticConstellation } from "./SemanticConstellation";

const PROFESSIONS = [
  "ingeniería de software",
  "enfermería",
  "arquitectura",
  "marketing",
  "docencia",
  "diseño de producto",
  "derecho",
];

const EASE = [0.2, 0.8, 0.2, 1] as const;

export function LivingHero() {
  const [profIndex, setProfIndex] = useState(0);
  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const apply = () => setIsDesktop(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  useEffect(() => {
    const t = setInterval(() => {
      setProfIndex((i) => (i + 1) % PROFESSIONS.length);
    }, 2600);
    return () => clearInterval(t);
  }, []);

  return (
    <section
      id="top"
      className="relative flex min-h-[100svh] flex-col justify-center overflow-hidden pt-28 pb-16 md:pt-32"
    >
      {/* Full-bleed living graph */}
      <SemanticConstellation
        className="absolute inset-0 h-full w-full"
        showLabels={isDesktop}
        interactive
        intensity={isDesktop ? 1 : 0.85}
      />

      {/* Legibility scrim — dark where the copy sits, clear where the graph glows */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "linear-gradient(105deg, var(--cos-bg) 0%, rgba(7,8,10,0.86) 34%, rgba(7,8,10,0.35) 62%, rgba(7,8,10,0) 100%)",
        }}
      />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-[var(--cos-bg)] to-transparent" />

      <div className="relative z-10 mx-auto w-full max-w-7xl px-5 md:px-8">
        <div className="max-w-2xl">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE }}
          >
            <span className="cos-chip">
              <span className="h-1.5 w-1.5 rounded-full bg-[#00d4aa] shadow-[0_0_10px_1px_rgba(0,212,170,0.8)]" />
              Career OS · con servidor MCP propio
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 22 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.08, ease: EASE }}
            className="cos-display mt-7"
            style={{ fontSize: "clamp(44px, 7vw, 88px)", lineHeight: 0.98 }}
          >
            Tu carrera no es
            <br />
            un CV. Es un{" "}
            <span className="relative whitespace-nowrap">
              <span
                style={{
                  background: "linear-gradient(110deg,#ffda6e 0%,#6ece9d 52%,#00d4aa 100%)",
                  WebkitBackgroundClip: "text",
                  backgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                universo
              </span>
              .
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2, ease: EASE }}
            className="mt-6 max-w-xl text-[17px] leading-relaxed text-[var(--cos-stone)] md:text-lg"
          >
            Un grafo de conocimiento vivo de tu trayectoria que un equipo de agentes
            mantiene al día — y del que nacen CVs y cartas a medida en segundos.
          </motion.p>

          {/* Morphing profession line — a standalone chip, never mid-sentence */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.32, ease: EASE }}
            className="mt-5 flex items-center gap-2 text-sm text-[var(--cos-faint)]"
          >
            <span>Hecho para</span>
            <span className="inline-flex h-7 items-center overflow-hidden rounded-full border border-[var(--cos-hairline)] bg-[var(--cos-fill)] px-3">
              <AnimatePresence mode="wait">
                <motion.span
                  key={PROFESSIONS[profIndex]}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.32, ease: EASE }}
                  className="font-medium text-[var(--cos-ink)]"
                >
                  {PROFESSIONS[profIndex]}
                </motion.span>
              </AnimatePresence>
            </span>
            <span>y cualquier profesión.</span>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.42, ease: EASE }}
            className="mt-9 flex flex-col items-start gap-3 sm:flex-row sm:items-center"
          >
            <button
              onClick={() => (window.location.hash = "#/register")}
              className="cos-btn-primary group w-full sm:w-auto"
            >
              Crear mi universo gratis
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
            </button>
            <button
              onClick={() => {
                document.getElementById("como")?.scrollIntoView({ behavior: "smooth" });
              }}
              className="cos-btn-ghost w-full sm:w-auto"
            >
              <Sparkles size={15} />
              Ver cómo funciona
            </button>
          </motion.div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="mt-5 text-xs text-[var(--cos-faint)]"
          >
            Sin tarjeta · plan gratuito con universo completo · RGPD, hosting UE
          </motion.p>
        </div>
      </div>

      {/* Floating "live" stat — desktop only, sells the living graph */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8, delay: 0.7, ease: EASE }}
        className="cos-panel absolute bottom-10 right-8 z-10 hidden items-center gap-3 rounded-2xl px-4 py-3 lg:flex"
      >
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#6ece9d] opacity-60" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-[#6ece9d]" />
        </span>
        <div className="leading-tight">
          <div className="font-mono text-sm text-[var(--cos-ink)]">142 entidades · 318 conexiones</div>
          <div className="text-[11px] text-[var(--cos-faint)]">tu universo, actualizándose en vivo</div>
        </div>
      </motion.div>
    </section>
  );
}
