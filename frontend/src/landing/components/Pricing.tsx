import { motion } from "motion/react";
import { ArrowRight, Check } from "lucide-react";
import { useTranslation } from "react-i18next";

import { SectionHeading } from "./SectionHeading";

const EASE = [0.2, 0.8, 0.2, 1] as const;

// Prices mirror billing PLAN_LIMITS — keep in sync with the backend plans.
const TIERS = [
  { id: "free", name: "Free", price: "€0", accent: "#6ece9d" },
  { id: "premium", name: "Premium", price: "€9,99", accent: "#ffda6e", featured: true },
  { id: "pro", name: "Pro", price: "€19,99", accent: "#00d4aa" },
] as const;

export function Pricing() {
  const { t } = useTranslation("landing");

  return (
    <section className="relative py-28 md:py-36">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <SectionHeading
          eyebrow={t("pricing.eyebrow")}
          accent="#ffda6e"
          title={
            <>
              {t("pricing.title1")}
              <br />
              <span className="cos-dim">{t("pricing.title2")}</span>
            </>
          }
          subtitle={t("pricing.sub")}
        />

        <div className="mt-16 grid gap-5 md:grid-cols-3">
          {TIERS.map((tier, i) => {
            const features = t(`pricing.tiers.${tier.id}.features`, {
              returnObjects: true,
            }) as string[];
            const period =
              tier.id === "free"
                ? t("pricing.forever")
                : t(`pricing.tiers.${tier.id}.period`);
            const featured = "featured" in tier && tier.featured;
            return (
              <motion.div
                key={tier.id}
                initial={{ opacity: 0, y: 28 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.55, delay: i * 0.1, ease: EASE }}
                className={`relative flex flex-col rounded-3xl p-6 md:p-7 ${
                  featured
                    ? "border border-[#ffda6e]/40 bg-[var(--cos-fill-strong)]"
                    : "cos-panel"
                }`}
                style={
                  featured
                    ? {
                        boxShadow:
                          "0 0 0 1px rgba(255,218,110,0.2), 0 30px 80px -40px rgba(255,218,110,0.35)",
                      }
                    : undefined
                }
              >
                {featured && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[#ffda6e] px-3 py-1 text-[11px] font-semibold text-[#2a2003]">
                    {t("pricing.popular")}
                  </span>
                )}

                <div className="mb-1 text-sm font-medium" style={{ color: tier.accent }}>
                  {tier.name}
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="cos-display text-4xl text-[var(--cos-ink)]">{tier.price}</span>
                  <span className="text-xs text-[var(--cos-faint)]">{period}</span>
                </div>
                <p className="mt-3 text-sm text-[var(--cos-stone)]">
                  {t(`pricing.tiers.${tier.id}.tagline`)}
                </p>

                <div className="my-6 h-px bg-[var(--cos-hairline)]" />

                <ul className="flex flex-1 flex-col gap-3">
                  {features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-[var(--cos-ink)]">
                      <Check size={16} className="mt-0.5 shrink-0" style={{ color: tier.accent }} />
                      {f}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => (window.location.hash = "#/register")}
                  className={`group mt-7 inline-flex w-full items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-semibold transition-all ${
                    featured
                      ? "cos-btn-primary"
                      : "border border-[var(--cos-hairline-strong)] text-[var(--cos-ink)] hover:bg-[var(--cos-fill-strong)]"
                  }`}
                >
                  {t(`pricing.tiers.${tier.id}.cta`)}
                  <ArrowRight size={15} className="transition-transform group-hover:translate-x-0.5" />
                </button>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
