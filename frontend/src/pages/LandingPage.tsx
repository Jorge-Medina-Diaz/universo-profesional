import { useState } from "react";
import { motion } from "motion/react";
import { ChevronDown, ArrowRight } from "lucide-react";
import {
  SiteNav,
  LivingHero,
  LogoMarquee,
  OldWayNewWay,
  MoatPillars,
  ProactiveCapture,
  AuditMilestones,
  CvGenerationDemo,
  UseCaseConstellation,
  McpSection,
  Pricing,
  FloatingStat,
  TestimonialCard,
} from "@/landing/components";

const EASE = [0.2, 0.8, 0.2, 1] as const;

const FAQS = [
  {
    q: "¿Qué es exactamente un «Universo Profesional»?",
    a: "Un grafo de conocimiento vivo de tu trayectoria: experiencias, educación, proyectos, habilidades, certificaciones e idiomas conectados entre sí. A diferencia de un CV estático, crece, se conecta y evoluciona contigo.",
  },
  {
    q: "¿Necesito saber de IA para usarlo?",
    a: "No. Conversas en lenguaje natural. Cuéntale tu semana («esta semana trabajé en…») y el agente pregunta lo justo para estructurar tu información. Sin formularios, sin plantillas.",
  },
  {
    q: "¿Es solo para ingenieros de software?",
    a: "Nació pensado para ingeniería de software —es lo que más dominamos— pero es agnóstico por diseño. Funciona igual de bien en sanidad, arquitectura, marketing, educación u hostelería: el agente adapta el descubrimiento y los documentos a tu sector.",
  },
  {
    q: "¿Mis datos están seguros?",
    a: "Sí. RGPD desde el origen, hosting en la UE, cifrado en reposo y en tránsito, y aislamiento por usuario en base de datos. Nunca entrenamos modelos con tus datos sin tu consentimiento.",
  },
  {
    q: "¿Qué significa «MCP nativo»?",
    a: "MCP es el estándar abierto para conectar agentes con herramientas. Nuestro servidor permite que Claude, Cursor o Codex gestionen tu perfil y generen documentos en lenguaje natural, con OAuth 2.1.",
  },
  {
    q: "¿Puedo exportar mis documentos?",
    a: "Sí. Generamos CVs y cartas en PDF (tipografía profesional) y DOCX editable, además de JSON Resume. Tu universo siempre es exportable: tus datos son tuyos.",
  },
];

export function LandingPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  return (
    <div className="landing-cosmos min-h-screen">
      <SiteNav />

      <LivingHero />

      <LogoMarquee />

      <OldWayNewWay />

      <MoatPillars />

      {/* Engine stats strip */}
      <section className="border-y border-[var(--cos-hairline)] py-16">
        <div className="mx-auto grid max-w-5xl grid-cols-2 gap-8 px-5 md:grid-cols-4 md:px-8">
          <FloatingStat value={1536} label="Dimensiones vectoriales" />
          <FloatingStat value={99} suffix="%" label="Precisión de fusión" accent="#6ece9d" />
          <FloatingStat value={40} prefix="<" suffix="ms" label="Latencia MCP" accent="#00d4aa" />
          <FloatingStat value={28} label="Idiomas soportados" accent="#ffda6e" />
        </div>
      </section>

      <ProactiveCapture />

      <AuditMilestones />

      <CvGenerationDemo />

      <UseCaseConstellation />

      <McpSection />

      {/* Testimonials */}
      <section className="relative py-28 md:py-36">
        <div className="mx-auto max-w-6xl px-5 md:px-8">
          <div className="mb-14 text-center">
            <span className="cos-eyebrow mb-5 inline-flex">Lo dicen ellos</span>
            <h2 className="cos-display text-[clamp(32px,5vw,56px)] leading-[1.02]">
              Resultados que <span className="cos-dim">hablan.</span>
            </h2>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            <TestimonialCard
              quote="Mi mejor trabajo vivía en PRs e incidencias que nadie veía. Ahora genero un CV alineado a cada oferta en 30 segundos, con mis logros reales y bien contados."
              author="Daniel R."
              role="Backend Engineer"
              metric="-90%"
              metricLabel="tiempo en CVs"
              delay={0}
            />
            <TestimonialCard
              quote="El agente detectó una certificación que había olvidado y la fusionó sola. Generar un CV para una oposición sanitaria pasó de un fin de semana a un minuto."
              author="Elena M."
              role="Enfermera de Urgencias"
              metric="+34%"
              metricLabel="completitud"
              delay={0.1}
            />
            <TestimonialCard
              quote="La detección de gaps me dijo exactamente qué me faltaba para dar el salto a dirección. Lo usé como plan de desarrollo durante un año."
              author="Sofía L."
              role="Directora de Marketing"
              metric="3x"
              metricLabel="entrevistas"
              delay={0.2}
            />
          </div>
        </div>
      </section>

      <Pricing />

      {/* Final CTA */}
      <section className="relative overflow-hidden py-32 md:py-44">
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(60% 60% at 50% 45%, rgba(255,218,110,0.1) 0%, transparent 60%), radial-gradient(50% 50% at 70% 70%, rgba(0,212,170,0.08) 0%, transparent 60%)",
          }}
        />
        <div className="relative z-10 mx-auto max-w-3xl px-5 text-center md:px-8">
          <motion.span
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, ease: EASE }}
            className="cos-chip mb-7"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-[#6ece9d] shadow-[0_0_10px_1px_rgba(110,206,157,0.8)]" />
            Beta abierta · plan gratuito para siempre
          </motion.span>
          <motion.h2
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, ease: EASE }}
            className="cos-display text-[clamp(44px,8vw,92px)] leading-[0.98]"
          >
            Tu universo
            <br />
            <span
              style={{
                background: "linear-gradient(110deg,#ffda6e 0%,#6ece9d 52%,#00d4aa 100%)",
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              te espera.
            </span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, delay: 0.15 }}
            className="mx-auto mt-6 max-w-md text-[var(--cos-stone)] md:text-lg"
          >
            Empieza gratis. Construye tu grafo, conecta tu agente y descubre posibilidades que
            un CV nunca podría mostrar.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.25, ease: EASE }}
            className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row"
          >
            <button
              onClick={() => (window.location.hash = "#/register")}
              className="cos-btn-primary group w-full sm:w-auto"
            >
              Crear mi universo gratis
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
            </button>
            <button
              onClick={() => (window.location.hash = "#/login")}
              className="cos-btn-ghost w-full sm:w-auto"
            >
              Iniciar sesión
            </button>
          </motion.div>
          <p className="mt-6 text-xs text-[var(--cos-faint)]">
            Sin tarjeta · 7 días de Premium gratis · cancela cuando quieras
          </p>
        </div>
      </section>

      {/* FAQ */}
      <section className="relative py-28 md:py-36">
        <div className="mx-auto max-w-2xl px-5 md:px-8">
          <div className="mb-14 text-center">
            <span className="cos-eyebrow mb-5 inline-flex">Dudas</span>
            <h2 className="cos-display text-[clamp(32px,5vw,56px)] leading-[1.02]">
              Preguntas <span className="cos-dim">frecuentes.</span>
            </h2>
          </div>
          <div className="space-y-3">
            {FAQS.map((faq, i) => (
              <motion.div
                key={i}
                className="cos-panel overflow-hidden"
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05, ease: EASE }}
              >
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="flex w-full items-center justify-between p-5 text-left"
                >
                  <span className="pr-4 text-sm font-medium text-[var(--cos-ink)]">{faq.q}</span>
                  <ChevronDown
                    size={16}
                    className={`shrink-0 text-[var(--cos-faint)] transition-transform duration-300 ${
                      openFaq === i ? "rotate-180" : ""
                    }`}
                  />
                </button>
                <motion.div
                  initial={false}
                  animate={{
                    height: openFaq === i ? "auto" : 0,
                    opacity: openFaq === i ? 1 : 0,
                  }}
                  transition={{ duration: 0.3, ease: EASE }}
                  className="overflow-hidden"
                >
                  <p className="px-5 pb-5 text-sm leading-relaxed text-[var(--cos-stone)]">{faq.a}</p>
                </motion.div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[var(--cos-hairline)] py-14">
        <div className="mx-auto max-w-6xl px-5 md:px-8">
          <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
            <div className="flex items-center gap-2.5">
              <span className="relative grid h-6 w-6 place-items-center">
                <span className="absolute h-2 w-2 rounded-full bg-[#ffda6e] shadow-[0_0_12px_2px_rgba(255,218,110,0.6)]" />
                <span className="absolute h-6 w-6 rounded-full border border-[var(--cos-hairline)]" />
              </span>
              <span className="cos-display text-base text-[var(--cos-ink)]">Universo Profesional</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-[var(--cos-stone)]">
              <a href="#/privacy" className="transition-colors hover:text-[var(--cos-ink)]">Privacidad</a>
              <a href="#/terms" className="transition-colors hover:text-[var(--cos-ink)]">Términos</a>
              <a href="#/mcp" className="transition-colors hover:text-[var(--cos-ink)]">MCP</a>
            </div>
            <p className="text-xs text-[var(--cos-faint)]">
              © {new Date().getFullYear()} Universo Profesional · AGPL-3.0
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
