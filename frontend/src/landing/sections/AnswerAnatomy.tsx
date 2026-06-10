import { motion } from "motion/react";
import { Award, Briefcase, FolderGit } from "lucide-react";
import { useTranslation } from "react-i18next";

import { SectionHeading } from "@/landing/components/SectionHeading";

const EASE = [0.2, 0.8, 0.2, 1] as const;
const LANE_COLORS = ["#ffda6e", "#6ece9d", "#00d4aa", "#f4f1ea"];
const EV_ICONS = [Briefcase, FolderGit, Award];

/** §6 v2 — depth without jargon: what happens in the second between a
 *  recruiter's question and an evidence-backed answer. Replaces the old
 *  "engine room" table; the technical facts shrink to one mono strip. */
export function AnswerAnatomy() {
  const { t } = useTranslation("landing");
  const lanes = t("anatomy.lanes", { returnObjects: true }) as string[];
  const evidences = [
    t("anatomy.ev1", { returnObjects: true }),
    t("anatomy.ev2", { returnObjects: true }),
    t("anatomy.ev3", { returnObjects: true }),
  ] as { kind: string; text: string }[];

  return (
    <section className="py-24 md:py-32 px-5" aria-label={t("anatomy.title")}>
      <div className="mx-auto max-w-5xl">
        <SectionHeading
          eyebrow={t("anatomy.eyebrow")}
          title={<span className="cos-gradient-text">{t("anatomy.title")}</span>}
          subtitle={t("anatomy.sub")}
          accent="#00d4aa"
        />

        <div className="mt-14 flex flex-col gap-0">
          {/* 1 — the question */}
          <Step n={1} label={t("anatomy.s1")}>
            <p className="font-display text-[clamp(20px,2.6vw,28px)] text-[var(--cos-ink)]">
              {t("anatomy.s1q")}
            </p>
          </Step>

          {/* 2 — four directions at once */}
          <Step n={2} label={t("anatomy.s2")}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {lanes.map((lane, i) => (
                <motion.div
                  key={lane}
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-60px" }}
                  transition={{ duration: 0.45, ease: EASE, delay: i * 0.12 }}
                  className="rounded-xl border border-[var(--cos-hairline)] bg-[var(--cos-panel)] px-3 py-3.5 text-center"
                >
                  <motion.span
                    aria-hidden
                    className="mx-auto mb-2 block h-1.5 w-8 rounded-full"
                    style={{ background: LANE_COLORS[i] }}
                    initial={{ scaleX: 0 }}
                    whileInView={{ scaleX: 1 }}
                    viewport={{ once: true, margin: "-60px" }}
                    transition={{ duration: 0.6, ease: EASE, delay: 0.3 + i * 0.12 }}
                  />
                  <span className="text-[13px] text-[var(--cos-ink)]">{lane}</span>
                </motion.div>
              ))}
            </div>
          </Step>

          {/* 3 — evidence found */}
          <Step n={3} label={t("anatomy.s3")}>
            <div className="grid md:grid-cols-3 gap-3">
              {evidences.map((ev, i) => {
                const Icon = EV_ICONS[i];
                return (
                  <motion.div
                    key={ev.text}
                    initial={{ opacity: 0, y: 12 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: "-60px" }}
                    transition={{ duration: 0.5, ease: EASE, delay: 0.15 + i * 0.15 }}
                    className="rounded-xl border border-[var(--cos-hairline)] bg-[var(--cos-panel-raised)] p-4"
                  >
                    <div className="flex items-center gap-1.5 mb-2 text-[var(--cos-stone)]">
                      <Icon size={13} aria-hidden />
                      <span className="text-[10px] uppercase tracking-wide">{ev.kind}</span>
                    </div>
                    <p className="text-[13px] text-[var(--cos-ink)] leading-relaxed">{ev.text}</p>
                  </motion.div>
                );
              })}
            </div>
          </Step>

          {/* 4 — the grounded answer */}
          <Step n={4} label={t("anatomy.s4")} last>
            <p className="text-[15px] text-[var(--cos-stone)] leading-relaxed max-w-xl">
              {t("anatomy.s4detail")}
            </p>
          </Step>
        </div>

        <p className="mt-12 text-center text-[10.5px] font-mono text-[var(--cos-faint)]">
          {t("anatomy.techStrip")}
        </p>
      </div>
    </section>
  );
}

function Step({
  n,
  label,
  children,
  last,
}: {
  n: number;
  label: string;
  children: React.ReactNode;
  last?: boolean;
}) {
  return (
    <div className="grid grid-cols-[40px_1fr] gap-5">
      <div className="flex flex-col items-center">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-[#00d4aa]/40 text-[12px] font-mono text-[#00d4aa]">
          {n}
        </span>
        {!last && <span aria-hidden className="w-px flex-1 bg-[var(--cos-hairline)] my-2" />}
      </div>
      <div className={last ? "pb-2" : "pb-10"}>
        <p className="text-[11px] font-mono uppercase tracking-[0.16em] text-[var(--cos-stone)] mb-3 mt-2">
          {label}
        </p>
        {children}
      </div>
    </div>
  );
}
