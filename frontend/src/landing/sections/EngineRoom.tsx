import { motion } from "motion/react";
import { useTranslation } from "react-i18next";

import { SectionHeading } from "@/landing/components/SectionHeading";

const EASE = [0.2, 0.8, 0.2, 1] as const;

const LANES = [
  { key: "bm25", color: "#ffda6e" },
  { key: "dense", color: "#6ece9d" },
  { key: "ppr", color: "#00d4aa" },
  { key: "comm", color: "#f4f1ea" },
] as const;

/** §7 — credibility through real internals (the Linear move). Hard rule:
 *  every fact on this band is reproducible from the repo. Mono = true. */
export function EngineRoom() {
  const { t } = useTranslation("landing");
  const facts = t("engine.facts", { returnObjects: true }) as string[];

  return (
    <section id="engine" className="cosmos-deep py-24 md:py-32 px-5" aria-label={t("engine.title")}>
      <div className="mx-auto max-w-5xl">
        <SectionHeading
          eyebrow={t("engine.eyebrow")}
          title={t("engine.title")}
          subtitle={t("engine.sub")}
          accent="#00d4aa"
        />

        {/* 4-lane retrieval diagram: query → lanes → RRF fusion */}
        <div className="mt-14 rounded-2xl border border-[var(--cos-hairline)] bg-[var(--cos-panel)] p-6 md:p-8 overflow-x-auto">
          <div className="min-w-[560px]">
            <div className="flex items-center gap-2 mb-6">
              <span className="text-[11px] font-mono text-[var(--cos-faint)]">query</span>
              <span aria-hidden className="h-px flex-1 bg-[var(--cos-hairline)]" />
            </div>
            <div className="grid grid-cols-4 gap-3">
              {LANES.map((lane, i) => (
                <motion.div
                  key={lane.key}
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-80px" }}
                  transition={{ duration: 0.5, ease: EASE, delay: i * 0.12 }}
                  className="rounded-xl border border-[var(--cos-hairline)] bg-[var(--cos-fill)] px-3 py-4 text-center"
                >
                  <span
                    aria-hidden
                    className="mx-auto mb-2 block h-1.5 w-1.5 rounded-full"
                    style={{ background: lane.color }}
                  />
                  <span className="text-[12px] font-mono text-[var(--cos-stone)]">
                    {t(`engine.lanes.${lane.key}`)}
                  </span>
                </motion.div>
              ))}
            </div>
            <div className="flex flex-col items-center mt-5">
              <motion.span
                aria-hidden
                initial={{ scaleY: 0 }}
                whileInView={{ scaleY: 1 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.4, ease: EASE, delay: 0.5 }}
                className="block w-px h-7 bg-[var(--cos-hairline-strong)] origin-top"
              />
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.5, ease: EASE, delay: 0.7 }}
                className="rounded-full border border-[var(--cos-nova)]/40 px-5 py-2.5 text-[12px] font-mono text-[var(--cos-ink)]"
                style={{ boxShadow: "0 0 24px rgba(0,212,170,0.2)" }}
              >
                <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--cos-nova)] mr-2 align-middle" />
                {t("engine.fusion")}
              </motion.div>
            </div>
          </div>
        </div>

        {/* reproducible-facts table */}
        <div className="mt-10 flex flex-col">
          {facts.map((fact, i) => (
            <motion.div
              key={fact}
              initial={{ opacity: 0, x: -10 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.45, ease: EASE, delay: i * 0.06 }}
              className="flex items-start gap-3 py-3 border-b border-[var(--cos-hairline)] first:border-t"
            >
              <span className="text-[11px] font-mono text-[var(--cos-faint)] mt-0.5 w-6 shrink-0">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="text-[13px] font-mono text-[var(--cos-stone)] leading-relaxed">{fact}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
