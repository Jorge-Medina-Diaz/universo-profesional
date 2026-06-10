import { motion } from "motion/react";
import { useTranslation } from "react-i18next";

const EASE = [0.2, 0.8, 0.2, 1] as const;

/** §2 — the enemy, named in one breath. Bare background; the silence IS the
 *  design. One display-scale paragraph, word-group reveal, two treated words. */
export function Manifesto() {
  const { t } = useTranslation("landing");
  const lines = [
    { text: t("manifesto.p1"), cls: "text-[var(--cos-ink)]" },
    { text: t("manifesto.p2"), cls: "text-[var(--cos-dim-color)]" },
    { text: t("manifesto.p3"), cls: "text-[var(--cos-ink)] font-medium" },
    { text: t("manifesto.p4"), cls: "text-[var(--cos-stone)]" },
  ];

  return (
    <section className="py-28 md:py-40 px-5" aria-label="Manifesto">
      <div className="mx-auto max-w-3xl">
        <p className="font-display leading-[1.18] text-[clamp(26px,3.6vw,44px)]">
          {lines.map((line, i) => (
            <motion.span
              key={i}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.7, ease: EASE, delay: i * 0.28 }}
              className={`block ${line.cls} ${i > 0 ? "mt-4" : ""}`}
            >
              {line.text}
            </motion.span>
          ))}
        </p>
      </div>
    </section>
  );
}
