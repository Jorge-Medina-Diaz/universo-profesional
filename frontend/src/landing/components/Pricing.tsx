import { motion } from "motion/react";
import { Check, ArrowRight } from "lucide-react";
import { SectionHeading } from "./SectionHeading";

interface Tier {
  id: string;
  name: string;
  price: string;
  period: string;
  tagline: string;
  features: string[];
  cta: string;
  featured?: boolean;
  accent: string;
}

const TIERS: Tier[] = [
  {
    id: "free",
    name: "Free",
    price: "€0",
    period: "para siempre",
    tagline: "Tu universo completo, gratis.",
    features: [
      "Universo de conocimiento completo",
      "Agentes de captura y descubrimiento",
      "3 CVs / mes · 1 carta / mes",
      "Exporta a PDF, DOCX y JSON Resume",
    ],
    cta: "Crear mi universo",
    accent: "#6ece9d",
  },
  {
    id: "premium",
    name: "Premium",
    price: "€9,99",
    period: "/ mes · €89 al año",
    tagline: "Sin límites + tu agente en todas partes.",
    features: [
      "Todo lo de Free, sin límites",
      "CVs y cartas ilimitados",
      "Servidor MCP · 200 llamadas/día",
      "Auditoría e hitos de carrera",
      "Soporte prioritario",
    ],
    cta: "Probar 7 días gratis",
    featured: true,
    accent: "#ffda6e",
  },
  {
    id: "pro",
    name: "Pro",
    price: "€19,99",
    period: "/ mes · €179 al año",
    tagline: "Para quien vive dentro de sus agentes.",
    features: [
      "Todo lo de Premium",
      "Servidor MCP · 1.000 llamadas/día",
      "Máxima prioridad de cómputo",
      "Acceso anticipado a nuevas capas",
    ],
    cta: "Empezar con Pro",
    accent: "#00d4aa",
  },
];

const EASE = [0.2, 0.8, 0.2, 1] as const;

export function Pricing() {
  return (
    <section id="precios" className="relative py-28 md:py-36">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <SectionHeading
          eyebrow="Precios"
          accent="#ffda6e"
          title={
            <>
              Empieza gratis.
              <br />
              <span className="cos-dim">Crece cuando quieras.</span>
            </>
          }
          subtitle="Sin tarjeta para empezar. 7 días de Premium gratis al registrarte. Cancela cuando quieras."
        />

        <div className="mt-16 grid gap-5 md:grid-cols-3">
          {TIERS.map((tier, i) => (
            <motion.div
              key={tier.id}
              initial={{ opacity: 0, y: 28 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.55, delay: i * 0.1, ease: EASE }}
              className={`relative flex flex-col rounded-3xl p-6 md:p-7 ${
                tier.featured
                  ? "border border-[#ffda6e]/40 bg-[var(--cos-fill-strong)]"
                  : "cos-panel"
              }`}
              style={
                tier.featured
                  ? {
                      boxShadow:
                        "0 0 0 1px rgba(255,218,110,0.2), 0 30px 80px -40px rgba(255,218,110,0.35)",
                    }
                  : undefined
              }
            >
              {tier.featured && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[#ffda6e] px-3 py-1 text-[11px] font-semibold text-[#2a2003]">
                  Más popular
                </span>
              )}

              <div className="mb-1 text-sm font-medium" style={{ color: tier.accent }}>
                {tier.name}
              </div>
              <div className="flex items-baseline gap-2">
                <span className="cos-display text-4xl text-[var(--cos-ink)]">{tier.price}</span>
                <span className="text-xs text-[var(--cos-faint)]">{tier.period}</span>
              </div>
              <p className="mt-3 text-sm text-[var(--cos-stone)]">{tier.tagline}</p>

              <div className="my-6 h-px bg-[var(--cos-hairline)]" />

              <ul className="flex flex-1 flex-col gap-3">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-sm text-[var(--cos-ink)]">
                    <Check size={16} className="mt-0.5 shrink-0" style={{ color: tier.accent }} />
                    {f}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => (window.location.hash = "#/register")}
                className={`group mt-7 inline-flex w-full items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-semibold transition-all ${
                  tier.featured
                    ? "cos-btn-primary"
                    : "border border-[var(--cos-hairline-strong)] text-[var(--cos-ink)] hover:bg-[var(--cos-fill-strong)]"
                }`}
              >
                {tier.cta}
                <ArrowRight size={15} className="transition-transform group-hover:translate-x-0.5" />
              </button>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
