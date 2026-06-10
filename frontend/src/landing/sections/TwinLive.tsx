import { motion } from "motion/react";
import { useTranslation } from "react-i18next";

import { SectionHeading } from "@/landing/components/SectionHeading";
import { TwinChatCard } from "@/landing/components/TwinChatCard";
import { getReplays } from "@/landing/replays";

const EASE = [0.2, 0.8, 0.2, 1] as const;

/** §5 — the page's "wait, this is real" moment. The chat hits the
 *  PRODUCTION twin endpoint (slug `demo`): production RLS, production
 *  retrieval, production Haiku. Deep-space band; the honesty ledger is
 *  part of the design, not a disclaimer. */
export function TwinLive() {
  const { t, i18n } = useTranslation("landing");
  const replays = getReplays(i18n.language);

  const ledger = [t("twin.ledger1"), t("twin.ledger2"), t("twin.ledger3"), t("twin.ledger4")];
  const suggested = [t("twin.q1"), t("twin.q2"), t("twin.q3"), t("twin.q4")];

  return (
    <section id="twin" className="cosmos-deep py-24 md:py-32 px-5" aria-label={t("twin.title")}>
      <div className="mx-auto max-w-6xl">
        <SectionHeading
          eyebrow={t("twin.eyebrow")}
          title={t("twin.title")}
          subtitle={t("twin.sub")}
          accent="#00d4aa"
        />
        <div className="mt-14 grid lg:grid-cols-[1fr_1.1fr] gap-10 items-start">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.6, ease: EASE }}
            className="flex flex-col gap-0 order-2 lg:order-1"
          >
            {ledger.map((row) => (
              <div
                key={row}
                className="flex items-start gap-3 py-3.5 border-b border-[var(--cos-hairline)] first:border-t"
              >
                <span aria-hidden className="mt-1.5 h-1.5 w-1.5 rounded-full bg-[var(--cos-nova)] shrink-0" />
                <span className="text-[13px] font-mono text-[var(--cos-stone)] leading-relaxed">{row}</span>
              </div>
            ))}
            <p className="mt-6 text-sm text-[var(--cos-faint)]">
              {t("twin.emptyHint")}
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.7, ease: EASE, delay: 0.1 }}
            className="order-1 lg:order-2 rounded-2xl"
            style={{ boxShadow: "0 0 40px rgba(0, 212, 170, 0.15)" }}
          >
            <TwinChatCard
              slug="demo"
              suggested={suggested}
              height="h-[380px]"
              softCapTurns={6}
              labels={{
                emptyHint: t("twin.emptyHint"),
                softCapCta: t("twin.softCapCta"),
                replayBanner: t("twin.replayBanner"),
                offlineBanner: t("twin.offlineBanner"),
              }}
              fallbackReplay={replays.twinReplay}
            />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
