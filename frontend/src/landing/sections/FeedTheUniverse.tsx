import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { useTranslation } from "react-i18next";

import { MorphingPillTabs } from "@/landing/components/MorphingPillTabs";
import { SectionHeading } from "@/landing/components/SectionHeading";
import {
  SemanticConstellation,
  type ConstellationHandle,
  type ConstellationRegion,
} from "@/landing/components/SemanticConstellation";
import { getReplays, type FeedBeat } from "@/landing/replays";

const EASE = [0.2, 0.8, 0.2, 1] as const;

const FEED_REGIONS: ConstellationRegion[] = [
  { id: "exp", label: "Experiencia", color: "#ffda6e", cx: 0.3, cy: 0.3, count: 4, spread: 0.13 },
  { id: "skill", label: "Skills", color: "#6ece9d", cx: 0.68, cy: 0.42, count: 5, spread: 0.14 },
  { id: "proj", label: "Proyectos", color: "#00d4aa", cx: 0.4, cy: 0.72, count: 4, spread: 0.12 },
  { id: "edu", label: "Educación", color: "#6ece9d", cx: 0.75, cy: 0.78, count: 3, spread: 0.09 },
];

/** §3 — proof 1: talk, and watch the graph grow. A three-beat scripted chat
 *  replay (honestly simulated) whose committed cards fire nova pulses into a
 *  REAL canvas constellation that physically gains nodes. */
export function FeedTheUniverse() {
  const { t, i18n } = useTranslation("landing");
  const feed = getReplays(i18n.language).feed;
  const [tab, setTab] = useState<"day1" | "weekly" | "interview">("day1");
  const beat: FeedBeat = feed[tab];
  const [visible, setVisible] = useState(0);
  const constellation = useRef<ConstellationHandle>(null);
  const reduced =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    setVisible(0);
    if (reduced) {
      setVisible(beat.messages.length);
      beat.ignite.forEach((region) => constellation.current?.igniteNode(region));
      return;
    }
    let step = 0;
    const interval = window.setInterval(() => {
      step += 1;
      setVisible(step);
      const msg = beat.messages[step - 1];
      if (msg?.role === "card") {
        beat.ignite.forEach((region, j) => {
          window.setTimeout(
            () => constellation.current?.pulseFrom(0.06, 0.5, region),
            j * 260,
          );
        });
      }
      if (step >= beat.messages.length) window.clearInterval(interval);
    }, 1400);
    return () => window.clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, i18n.language]);

  return (
    <section id="producto" className="py-24 md:py-32 px-5" aria-label={t("feed.title")}>
      <div className="mx-auto max-w-6xl">
        <SectionHeading
          eyebrow={t("feed.eyebrow")}
          title={t("feed.title")}
          subtitle={t("feed.sub")}
          accent="#6ece9d"
        />

        <div className="mt-10 flex justify-center">
          <MorphingPillTabs
            tabs={[
              { id: "day1", label: t("feed.tabs.day1") },
              { id: "weekly", label: t("feed.tabs.weekly") },
              { id: "interview", label: t("feed.tabs.interview") },
            ]}
            active={tab}
            onChange={(id) => setTab(id as typeof tab)}
          />
        </div>

        <div className="mt-10 grid lg:grid-cols-2 gap-8 items-stretch">
          {/* chat replay */}
          <div className="rounded-2xl border border-[var(--cos-hairline)] bg-[var(--cos-panel)] p-5 flex flex-col">
            <div className="flex-1 flex flex-col gap-3 min-h-[300px]">
              {beat.messages.slice(0, visible).map((msg, i) =>
                msg.role === "card" ? (
                  <motion.div
                    key={`${tab}-${i}`}
                    initial={reduced ? false : { opacity: 0, scale: 0.96 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.4, ease: EASE }}
                    className="self-stretch rounded-xl border border-[var(--cos-leaf)]/40 bg-[var(--cos-fill)] px-4 py-3 text-[13px] font-mono text-[var(--cos-ink)]"
                  >
                    <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--cos-leaf)] mr-2 align-middle" />
                    {msg.text}
                  </motion.div>
                ) : (
                  <motion.div
                    key={`${tab}-${i}`}
                    initial={reduced ? false : { opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.35, ease: EASE }}
                    className={`max-w-[88%] rounded-2xl px-4 py-2.5 text-sm ${
                      msg.role === "user"
                        ? "self-end bg-[var(--cos-fill-strong)] text-[var(--cos-ink)]"
                        : "self-start border border-[var(--cos-hairline)] bg-[var(--cos-panel-raised)] text-[var(--cos-ink)]"
                    }`}
                  >
                    {msg.role === "agent" && (
                      <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--cos-nova)] mr-2 align-middle" />
                    )}
                    {msg.text}
                  </motion.div>
                ),
              )}
            </div>
            <p className="mt-4 pt-3 border-t border-[var(--cos-hairline)] text-xs text-[var(--cos-faint)]">
              {t(`feed.captions.${tab}`)}
            </p>
          </div>

          {/* the graph that grows */}
          <div className="relative rounded-2xl border border-[var(--cos-hairline)] bg-[var(--cos-fill)] min-h-[360px] overflow-hidden">
            <SemanticConstellation
              ref={constellation}
              key={tab}
              className="absolute inset-0"
              regions={FEED_REGIONS}
              intensity={0.7}
              interactive={false}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
