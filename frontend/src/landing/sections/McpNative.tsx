import { motion } from "motion/react";
import { useTranslation } from "react-i18next";

import { SectionHeading } from "@/landing/components/SectionHeading";

const EASE = [0.2, 0.8, 0.2, 1] as const;

const TERMINAL_LINES = [
  { kind: "cmd", text: "$ claude" },
  { kind: "dim", text: "connected · universo-profesional (MCP · OAuth 2.1)" },
  { kind: "dim", text: "tools: universe.search · universe.profile · documents.generate_cv · jobs.match" },
  { kind: "cmd", text: "> genera un CV para esta oferta de Backend Engineer" },
  { kind: "out", text: "✓ CV generado con 11 evidencias de tu universo → cv_backend_2026.pdf" },
] as const;

/** §8 — the agent-economy claim: your universe as tools in any MCP client. */
export function McpNative() {
  const { t } = useTranslation("landing");

  return (
    <section className="py-24 md:py-32 px-5" aria-label={t("mcp.title")}>
      <div className="mx-auto max-w-6xl grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <SectionHeading
            eyebrow={t("mcp.eyebrow")}
            title={t("mcp.title")}
            subtitle={t("mcp.sub")}
            align="left"
            accent="#00d4aa"
          />
          <div className="mt-7 flex flex-wrap gap-2">
            <span className="text-xs font-mono px-3 py-1.5 rounded-full border border-[var(--cos-hairline)] text-[var(--cos-stone)]">
              {t("mcp.clients")}
            </span>
            <span className="text-xs font-mono px-3 py-1.5 rounded-full border border-[var(--cos-hairline)] text-[var(--cos-stone)]">
              {t("mcp.byok")}
            </span>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.6, ease: EASE }}
          className="rounded-2xl overflow-hidden border border-[var(--cos-hairline)] bg-[#0b0d10] shadow-float"
        >
          <div className="flex items-center gap-1.5 px-4 py-3 border-b border-white/5">
            <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-white/15" />
            <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-white/15" />
            <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-white/15" />
          </div>
          <div className="px-5 py-5 font-mono text-[12.5px] leading-7">
            {TERMINAL_LINES.map((line, i) => (
              <motion.p
                key={i}
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ duration: 0.3, delay: 0.3 + i * 0.45 }}
                className={
                  line.kind === "cmd"
                    ? "text-[#f4f1ea]"
                    : line.kind === "out"
                      ? "text-[#6ece9d]"
                      : "text-[#6c6962]"
                }
              >
                {line.text}
              </motion.p>
            ))}
            <motion.span
              aria-hidden
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 2.8 }}
              className="inline-block w-2 h-4 bg-[#00d4aa] align-middle animate-pulse"
            />
          </div>
        </motion.div>
      </div>
    </section>
  );
}
