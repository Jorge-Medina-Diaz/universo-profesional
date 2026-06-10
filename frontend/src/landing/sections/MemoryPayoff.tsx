import { motion } from "motion/react";
import { FileText, Kanban, MessagesSquare, PenLine } from "lucide-react";
import { useTranslation } from "react-i18next";

import { SectionHeading } from "@/landing/components/SectionHeading";

const EASE = [0.2, 0.8, 0.2, 1] as const;

/** §7 v2 — the dividend, compact bento. CV/letters/prep/tracking are
 *  benefits OF the memory, one section, no pipelines. */
export function MemoryPayoff() {
  const { t } = useTranslation("landing");

  return (
    <section id="payoff" className="py-24 md:py-32 px-5" aria-label={t("payoff.title")}>
      <div className="mx-auto max-w-5xl">
        <SectionHeading
          eyebrow={t("payoff.eyebrow")}
          title={t("payoff.title")}
          subtitle={t("payoff.sub")}
          accent="#ffda6e"
        />

        <div className="mt-12 grid md:grid-cols-3 gap-4">
          {/* CV tile — double width, carries the honesty bar */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.55, ease: EASE }}
            className="md:col-span-2 rounded-2xl border border-[var(--cos-hairline)] bg-[var(--cos-panel-raised)] p-6"
          >
            <div className="flex items-center gap-2 mb-2 text-[var(--cos-stone)]">
              <FileText size={15} aria-hidden />
              <h3 className="text-[15px] font-medium text-[var(--cos-ink)]">
                {t("payoff.tiles.cv.title")}
              </h3>
            </div>
            <p className="text-sm text-[var(--cos-stone)] mb-4 max-w-md">{t("payoff.tiles.cv.body")}</p>
            <div className="flex flex-col gap-2 max-w-sm">
              <Bar label="Python" level={0.95} color="#6ece9d" />
              <Bar label="Kubernetes" level={0.7} color="#6ece9d" />
              <Bar label="Terraform" level={0.05} color="#d97706" note={t("payoff.tiles.cv.honesty")} />
            </div>
            <p className="mt-4 text-[10.5px] font-mono text-[var(--cos-faint)]">{t("payoff.formats")}</p>
          </motion.div>

          <Tile icon={<PenLine size={15} />} title={t("payoff.tiles.letters.title")} body={t("payoff.tiles.letters.body")} delay={0.1} />
          <Tile icon={<MessagesSquare size={15} />} title={t("payoff.tiles.prep.title")} body={t("payoff.tiles.prep.body")} delay={0.15} />
          <Tile icon={<Kanban size={15} />} title={t("payoff.tiles.tracking.title")} body={t("payoff.tiles.tracking.body")} delay={0.2} wide />
        </div>
      </div>
    </section>
  );
}

function Tile({
  icon,
  title,
  body,
  delay,
  wide,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  delay: number;
  wide?: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.55, ease: EASE, delay }}
      className={`rounded-2xl border border-[var(--cos-hairline)] bg-[var(--cos-panel)] p-6 ${wide ? "md:col-span-2" : ""}`}
    >
      <div className="flex items-center gap-2 mb-2 text-[var(--cos-stone)]">
        {icon}
        <h3 className="text-[15px] font-medium text-[var(--cos-ink)]">{title}</h3>
      </div>
      <p className="text-sm text-[var(--cos-stone)]">{body}</p>
    </motion.div>
  );
}

function Bar({ label, level, color, note }: { label: string; level: number; color: string; note?: string }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-[var(--cos-ink)]">{label}</span>
        {note && <span className="text-[10px] font-mono text-[#d97706]">{note}</span>}
      </div>
      <div className="h-1.5 rounded-full bg-[var(--cos-track)] overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          whileInView={{ width: `${Math.max(level * 100, 4)}%` }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.8, ease: EASE, delay: 0.3 }}
          className="h-full rounded-full"
          style={{ background: color }}
        />
      </div>
    </div>
  );
}
