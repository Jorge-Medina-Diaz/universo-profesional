import { useState } from "react";
import { motion } from "motion/react";
import { ChevronDown } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Pricing } from "@/landing/components/Pricing";

const EASE = [0.2, 0.8, 0.2, 1] as const;

/** §10 — pricing, the final ask, and a 5-item micro-FAQ. */
export function Closing() {
  const { t } = useTranslation("landing");
  const faqs = t("faq.items", { returnObjects: true }) as { q: string; a: string }[];
  const [open, setOpen] = useState<number | null>(null);

  const scrollToTwin = (e: React.MouseEvent) => {
    e.preventDefault();
    document.getElementById("twin")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <>
      <section id="precios" aria-label={t("nav.pricing")}>
        <Pricing />
      </section>

      <section className="py-28 md:py-36 px-5 text-center" aria-label={t("closing.title")}>
        <div className="mx-auto max-w-3xl">
          <motion.h2
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.7, ease: EASE }}
            className="font-display leading-[1.04] text-[clamp(36px,5.5vw,64px)]"
            style={{
              background: "linear-gradient(95deg, var(--cos-sun), var(--cos-leaf), var(--cos-nova))",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            {t("closing.title")}
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.15 }}
            className="mt-5 text-lg text-[var(--cos-stone)]"
          >
            {t("closing.sub")}
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.28 }}
            className="mt-9 flex flex-wrap items-center justify-center gap-3"
          >
            <a
              href="#/register"
              className="inline-flex items-center gap-2 h-12 px-7 rounded-full bg-[var(--cos-sun)] text-[#14130f] font-medium shadow-[0_0_0_1px_rgba(255,218,110,0.4),0_10px_30px_-10px_rgba(255,218,110,0.55)] hover:brightness-105 transition-all"
            >
              {t("closing.ctaPrimary")}
            </a>
            <a
              href="#twin"
              onClick={scrollToTwin}
              className="inline-flex items-center h-12 px-5 rounded-full border border-[var(--cos-hairline-strong)] text-[var(--cos-ink)] hover:bg-[var(--cos-fill-strong)] transition-colors"
            >
              {t("closing.ctaDemo")}
            </a>
          </motion.div>
          <p className="mt-5 text-xs text-[var(--cos-faint)]">{t("closing.honesty")}</p>
        </div>

        {/* micro-FAQ */}
        <div className="mx-auto max-w-2xl mt-24 text-left">
          <h3 className="text-[11px] font-mono uppercase tracking-[0.18em] text-[var(--cos-faint)] mb-4">
            {t("faq.title")}
          </h3>
          {faqs.map((item, i) => (
            <div key={item.q} className="border-b border-[var(--cos-hairline)] first:border-t">
              <button
                type="button"
                aria-expanded={open === i}
                onClick={() => setOpen(open === i ? null : i)}
                className="flex w-full items-center justify-between gap-4 py-4 text-left text-sm text-[var(--cos-ink)]"
              >
                {item.q}
                <ChevronDown
                  size={15}
                  aria-hidden
                  className={`shrink-0 text-[var(--cos-faint)] transition-transform duration-300 ${open === i ? "rotate-180" : ""}`}
                />
              </button>
              <motion.div
                initial={false}
                animate={{ height: open === i ? "auto" : 0, opacity: open === i ? 1 : 0 }}
                transition={{ duration: 0.3, ease: EASE }}
                className="overflow-hidden"
              >
                <p className="pb-4 text-sm text-[var(--cos-stone)] leading-relaxed">{item.a}</p>
              </motion.div>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
