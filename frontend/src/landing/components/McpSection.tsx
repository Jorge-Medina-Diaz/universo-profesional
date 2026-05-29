import { motion } from "motion/react";
import { Plug, ShieldCheck, Zap } from "lucide-react";
import { SectionHeading } from "./SectionHeading";

const EASE = [0.2, 0.8, 0.2, 1] as const;

const TOOL_CALLS = [
  { tool: "universe.add_achievement", arg: '"Charla en PyConES 2026"' },
  { tool: "universe.link_skill", arg: '"Public speaking"' },
  { tool: "documents.generate_cv", arg: 'job="acme-backend"' },
];

const FEATURES = [
  { icon: Plug, title: "Claude · Cursor · Codex", desc: "Streamable HTTP. Compatible con cualquier cliente MCP." },
  { icon: ShieldCheck, title: "OAuth 2.1 + DPoP", desc: "Autenticación de grado bancario para tus agentes." },
  { icon: Zap, title: "Lenguaje natural", desc: "«Genera un CV para esta oferta» — y está hecho." },
];

export function McpSection() {
  return (
    <section className="relative py-28 md:py-36">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          {/* Copy */}
          <div>
            <SectionHeading
              align="left"
              eyebrow="MCP nativo"
              accent="#00d4aa"
              title={
                <>
                  Tu universo, dentro
                  <br />
                  <span className="cos-dim">de tus herramientas.</span>
                </>
              }
              subtitle="El único Career OS con servidor MCP propio. Gestiona tu perfil y genera documentos sin salir de Claude, Cursor o tu terminal."
            />
            <div className="mt-8 flex flex-col gap-3">
              {FEATURES.map((f, i) => (
                <motion.div
                  key={f.title}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1, ease: EASE }}
                  className="flex items-start gap-3.5"
                >
                  <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-[var(--cos-hairline)] bg-[var(--cos-fill)] text-[#00d4aa]">
                    <f.icon size={16} />
                  </span>
                  <div>
                    <div className="text-sm font-medium text-[var(--cos-ink)]">{f.title}</div>
                    <div className="text-sm text-[var(--cos-faint)]">{f.desc}</div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Terminal */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.6, ease: EASE }}
            className="cos-panel-raised overflow-hidden rounded-2xl"
          >
            <div className="flex items-center gap-2 border-b border-[var(--cos-hairline)] px-4 py-3">
              <span className="h-3 w-3 rounded-full bg-[#e06a5b]/70" />
              <span className="h-3 w-3 rounded-full bg-[#ffda6e]/70" />
              <span className="h-3 w-3 rounded-full bg-[#6ece9d]/70" />
              <span className="ml-2 font-mono text-[11px] text-[var(--cos-faint)]">claude · universo-mcp</span>
            </div>
            <div className="space-y-3 p-5 font-mono text-[13px] leading-relaxed">
              <div className="text-[var(--cos-faint)]">
                <span className="text-[#6ece9d]">›</span> tú
              </div>
              <div className="text-[var(--cos-ink)]">
                Añade mi charla en la PyConES y genérame un CV para la oferta de Acme.
              </div>
              <div className="space-y-1.5 pt-1">
                {TOOL_CALLS.map((c, i) => (
                  <motion.div
                    key={c.tool}
                    initial={{ opacity: 0, x: -8 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.3 + i * 0.25, ease: EASE }}
                    className="flex items-center gap-2"
                  >
                    <span className="text-[#00d4aa]">⏺</span>
                    <span className="text-[var(--cos-stone)]">{c.tool}</span>
                    <span className="text-[var(--cos-faint)]">{c.arg}</span>
                    <motion.span
                      initial={{ opacity: 0 }}
                      whileInView={{ opacity: 1 }}
                      viewport={{ once: true }}
                      transition={{ delay: 0.55 + i * 0.25 }}
                      className="text-[#6ece9d]"
                    >
                      ✓
                    </motion.span>
                  </motion.div>
                ))}
              </div>
              <motion.div
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 1.3 }}
                className="flex items-center gap-2 border-t border-[var(--cos-hairline)] pt-3 text-[var(--cos-ink)]"
              >
                <span className="text-[#6ece9d]">✓</span> CV_Acme.pdf listo · 3 entidades nuevas
                <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-[#6ece9d]" />
              </motion.div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
