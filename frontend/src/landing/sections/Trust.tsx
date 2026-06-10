import { motion } from "motion/react";
import { useTranslation } from "react-i18next";

import { SectionHeading } from "@/landing/components/SectionHeading";

const EASE = [0.2, 0.8, 0.2, 1] as const;

/** §9 — ownership as mechanism claims (the Limitless move): mono mechanism +
 *  plain-language consequence. Hairline rows, no cards, no icons. */
export function Trust() {
  const { t } = useTranslation("landing");
  const rows = t("trust.rows", { returnObjects: true }) as { mech: string; plain: string }[];

  return (
    <section className="py-24 md:py-32 px-5" aria-label={t("trust.title")}>
      <div className="mx-auto max-w-3xl">
        <SectionHeading eyebrow={t("trust.eyebrow")} title={t("trust.title")} accent="#6ece9d" />
        <div className="mt-12 flex flex-col">
          {rows.map((row, i) => (
            <motion.div
              key={row.mech}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.5, ease: EASE, delay: i * 0.08 }}
              className="grid md:grid-cols-[220px_1fr] gap-2 md:gap-6 py-5 border-b border-[var(--cos-hairline)] first:border-t"
            >
              <span className="text-[13px] font-mono text-[var(--cos-ink)]">{row.mech}</span>
              <span className="text-sm text-[var(--cos-stone)] leading-relaxed">{row.plain}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
