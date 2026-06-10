import { useEffect, useRef } from "react";
import { motion } from "motion/react";
import { ArrowDown, ArrowRight } from "lucide-react";
import { useTranslation } from "react-i18next";

import { HeroLiveDemo } from "@/landing/components/HeroLiveDemo";
import {
  SemanticConstellation,
  type ConstellationHandle,
} from "@/landing/components/SemanticConstellation";

const EASE = [0.2, 0.8, 0.2, 1] as const;
const REGION_IDS = ["exp", "skill", "proj", "edu", "cert", "lang"];

/** §1 v2 — the product IS the hero: a generative-UI theater takes the stage
 *  (~55% desktop), the claim accompanies it. Dark, cinematic, gradient type. */
export function Hero() {
  const { t } = useTranslation("landing");
  const constellation = useRef<ConstellationHandle>(null);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;
    let i = 0;
    const interval = window.setInterval(() => {
      constellation.current?.pulseFrom(0.92, 0.94, REGION_IDS[i % REGION_IDS.length], false);
      i += 1;
    }, 7000);
    return () => window.clearInterval(interval);
  }, []);

  const scrollToTwin = (e: React.MouseEvent) => {
    e.preventDefault();
    document.getElementById("twin")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section className="relative min-h-[100svh] flex items-center overflow-hidden" aria-label="Universo Profesional">
      <SemanticConstellation
        ref={constellation}
        className="absolute inset-0 opacity-50"
        intensity={0.8}
        showLabels={false}
      />
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(120% 90% at 30% 40%, rgba(7,8,10,0.88) 0%, rgba(7,8,10,0.55) 55%, rgba(7,8,10,0.25) 100%)",
        }}
      />

      <div className="relative mx-auto w-full max-w-7xl px-5 md:px-10 pt-28 pb-16 grid lg:grid-cols-[45fr_55fr] gap-12 items-center">
        {/* the claim — short, never stacked */}
        <div>
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
            transition={{ duration: 0.8, ease: EASE, delay: 0.1 }}
            className="font-display leading-[1.0] text-[clamp(42px,5.2vw,76px)] text-[var(--cos-ink)]"
          >
            <span className="cos-gradient-text">{t("hero.title1")}</span>
            <br />
            {t("hero.title2")}
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.25 }}
            className="mt-6 text-[17px] leading-relaxed text-[var(--cos-stone)] max-w-md"
          >
            {t("hero.sub")}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.38 }}
            className="mt-8 flex flex-wrap items-center gap-3"
          >
            <a
              href="#/register"
              className="inline-flex items-center gap-2 h-12 px-6 rounded-full bg-[var(--cos-sun)] text-[#14130f] font-medium shadow-[0_0_0_1px_rgba(255,218,110,0.4),0_10px_40px_-10px_rgba(255,218,110,0.5)] hover:brightness-105 transition-all"
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

        {/* the product, live on stage */}
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.8, ease: EASE, delay: 0.2 }}
        >
          <HeroLiveDemo />
        </motion.div>
      </div>
    </section>
  );
}
