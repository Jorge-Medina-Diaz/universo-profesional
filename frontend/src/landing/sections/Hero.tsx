import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { ArrowDown, ArrowRight } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  SemanticConstellation,
  type ConstellationHandle,
} from "@/landing/components/SemanticConstellation";

const EASE = [0.2, 0.8, 0.2, 1] as const;
const REGION_IDS = ["exp", "skill", "proj", "edu", "cert", "lang"];

/** §1 — the claim + a constellation visibly FED by an agent: every ~6s a
 *  nova pulse leaves the "agent point" and ignites a real node. The mono
 *  counter reports what the canvas actually drew — true by construction. */
export function Hero() {
  const { t } = useTranslation("landing");
  const constellation = useRef<ConstellationHandle>(null);
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;
    let i = 0;
    const interval = window.setInterval(() => {
      // pulses originate bottom-right — where the agent dock lives in-app
      constellation.current?.pulseFrom(0.9, 0.92, REGION_IDS[i % REGION_IDS.length]);
      i += 1;
    }, 6000);
    return () => window.clearInterval(interval);
  }, []);

  const scrollToTwin = (e: React.MouseEvent) => {
    e.preventDefault();
    document.getElementById("twin")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section
      ref={sectionRef}
      className="relative min-h-[100svh] flex items-center overflow-hidden"
      aria-label="Universo Profesional"
    >
      <SemanticConstellation
        ref={constellation}
        className="absolute inset-0"
        intensity={1}
        onStats={(nodes, edges) => setStats({ nodes, edges })}
      />
      {/* diagonal legibility scrim over the copy side */}
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "linear-gradient(100deg, rgba(var(--cos-hero-scrim-rgb),0.94) 0%, rgba(var(--cos-hero-scrim-rgb),0.72) 44%, rgba(var(--cos-hero-scrim-rgb),0.06) 72%)",
        }}
      />

      <div className="relative mx-auto w-full max-w-7xl px-5 md:px-10 py-28">
        <div className="max-w-2xl">
          <motion.span
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: EASE }}
            className="inline-block text-[11px] font-mono uppercase tracking-[0.18em] text-[var(--cos-stone)] border border-[var(--cos-hairline)] rounded-full px-3 py-1.5 mb-7"
          >
            {t("hero.chip")}
          </motion.span>

          <motion.h1
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: EASE, delay: 0.08 }}
            className="font-display leading-[0.98] text-[clamp(44px,7vw,92px)] text-[var(--cos-ink)]"
          >
            {t("hero.title1")}
            <br />
            <span className="text-[var(--cos-dim-color)]">{t("hero.title2")}</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.22 }}
            className="mt-6 text-lg text-[var(--cos-stone)] max-w-xl"
          >
            {t("hero.sub")}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.34 }}
            className="mt-9 flex flex-wrap items-center gap-3"
          >
            <a
              href="#/register"
              className="inline-flex items-center gap-2 h-12 px-6 rounded-full bg-[var(--cos-sun)] text-[#14130f] font-medium shadow-[0_0_0_1px_rgba(255,218,110,0.4),0_10px_30px_-10px_rgba(255,218,110,0.55)] hover:brightness-105 transition-all"
            >
              {t("hero.ctaPrimary")} <ArrowRight size={16} aria-hidden />
            </a>
            <a
              href="#twin"
              onClick={scrollToTwin}
              className="inline-flex items-center gap-2 h-12 px-5 rounded-full border border-[var(--cos-hairline-strong)] text-[var(--cos-ink)] hover:bg-[var(--cos-fill-strong)] transition-colors"
            >
              {t("hero.ctaDemo")} <ArrowDown size={15} aria-hidden />
            </a>
          </motion.div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="mt-5 text-xs text-[var(--cos-faint)]"
          >
            {t("hero.honesty")}
          </motion.p>
        </div>
      </div>

      {/* TRUE counter of what this canvas drew (mono = true) */}
      <p
        aria-hidden
        className="absolute bottom-6 right-6 text-[11px] font-mono text-[var(--cos-faint)] bg-[var(--cos-label-bg)] border border-[var(--cos-hairline)] rounded-full px-3 py-1.5"
      >
        {t("hero.counter", { nodes: stats.nodes, edges: stats.edges })}
      </p>
    </section>
  );
}
