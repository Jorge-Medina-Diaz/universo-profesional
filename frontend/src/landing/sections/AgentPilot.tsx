import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { useTranslation } from "react-i18next";

import { MockupFrame } from "@/landing/components/MockupFrame";
import { SectionHeading } from "@/landing/components/SectionHeading";
import {
  SemanticConstellation,
  type ConstellationHandle,
  type ConstellationRegion,
} from "@/landing/components/SemanticConstellation";

const EASE = [0.2, 0.8, 0.2, 1] as const;
const SCENE_MS = 5000;

const PILOT_REGIONS: ConstellationRegion[] = [
  { id: "exp", label: "Experiencia", color: "#ffda6e", cx: 0.32, cy: 0.34, count: 4, spread: 0.12 },
  { id: "data", label: "Datos", color: "#00d4aa", cx: 0.68, cy: 0.55, count: 5, spread: 0.13 },
  { id: "proj", label: "Proyectos", color: "#6ece9d", cx: 0.42, cy: 0.74, count: 4, spread: 0.1 },
];

/** The agent's presence: a nova dot that glides to where the action happens. */
function AgentCursor({ x, y }: { x: string; y: string }) {
  return (
    <motion.span
      aria-hidden
      className="absolute z-20 h-3 w-3 rounded-full bg-[#00d4aa] pointer-events-none"
      style={{ boxShadow: "0 0 14px rgba(0,212,170,0.8), 0 0 40px rgba(0,212,170,0.3)" }}
      animate={{ left: x, top: y }}
      transition={{ duration: 0.9, ease: EASE }}
    />
  );
}

/** §6 — the Devin moment: one conversation pilots the entire app. A faithful
 *  scripted sequence (and labeled as such): navigation, generative cards,
 *  the constellation flying, diary capture. */
export function AgentPilot() {
  const { t } = useTranslation("landing");
  const [scene, setScene] = useState(0);
  const constellation = useRef<ConstellationHandle>(null);
  const reduced =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const scenes = [
    {
      command: t("pilot.scenes.s1"),
      title: "Candidaturas",
      body: "Kanban · 3 en entrevista · 5 aplicadas · 2 ofertas",
      cursor: { x: "16%", y: "22%" },
      kind: "navigate" as const,
    },
    {
      command: t("pilot.scenes.s2"),
      title: "Interview prep",
      body: "Brief de empresa · 12 preguntas probables · 3 historias STAR",
      cursor: { x: "48%", y: "58%" },
      kind: "card" as const,
    },
    {
      command: t("pilot.scenes.s3"),
      title: "Universo",
      body: "",
      cursor: { x: "72%", y: "40%" },
      kind: "graph" as const,
    },
    {
      command: t("pilot.scenes.s4"),
      title: "Diario",
      body: "+ Logro: migración cerrada — vinculado a Kubernetes",
      cursor: { x: "52%", y: "70%" },
      kind: "diary" as const,
    },
  ];

  useEffect(() => {
    if (reduced) return;
    const interval = window.setInterval(() => {
      setScene((s) => (s + 1) % scenes.length);
    }, SCENE_MS);
    return () => window.clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reduced]);

  useEffect(() => {
    const current = scenes[scene];
    if (current.kind === "graph") {
      constellation.current?.flyTo("data");
    } else {
      constellation.current?.flyTo(null);
      if (current.kind === "diary") constellation.current?.igniteNode("proj");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene]);

  const current = scenes[scene];

  return (
    <section className="py-24 md:py-32 px-5" aria-label={t("pilot.title")}>
      <div className="mx-auto max-w-6xl">
        <SectionHeading
          eyebrow={t("pilot.eyebrow")}
          title={t("pilot.title")}
          subtitle={t("pilot.sub")}
          accent="#00d4aa"
        />

        <div className="mt-12">
          <MockupFrame className="border border-[var(--cos-hairline)] shadow-float">
            <div className="relative grid md:grid-cols-[300px_1fr] min-h-[380px] bg-[var(--cos-bg-2)]">
              <AgentCursor x={current.cursor.x} y={current.cursor.y} />

              {/* the one conversation */}
              <div className="border-r border-[var(--cos-hairline)] p-4 flex flex-col gap-2.5 bg-[var(--cos-panel)]">
                <p className="text-[10px] font-mono uppercase tracking-[0.16em] text-[var(--cos-faint)] mb-1">
                  chat
                </p>
                {scenes.slice(0, scene + 1).map((s, i) => (
                  <motion.p
                    key={i}
                    initial={reduced ? false : { opacity: 0, y: 6 }}
                    animate={{ opacity: i === scene ? 1 : 0.45, y: 0 }}
                    transition={{ duration: 0.35, ease: EASE }}
                    className="self-end max-w-[95%] rounded-xl bg-[var(--cos-fill-strong)] px-3 py-2 text-[12.5px] text-[var(--cos-ink)]"
                  >
                    {s.command}
                  </motion.p>
                ))}
              </div>

              {/* the app surface the agent pilots */}
              <div className="relative p-5 overflow-hidden">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={scene}
                    initial={reduced ? false : { opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={reduced ? undefined : { opacity: 0, y: -8 }}
                    transition={{ duration: 0.4, ease: EASE }}
                    className="h-full"
                  >
                    <p className="text-[11px] font-mono text-[var(--cos-faint)] mb-3">
                      {current.title}
                    </p>
                    {current.kind === "graph" ? (
                      <div className="relative h-[280px] rounded-xl overflow-hidden border border-[var(--cos-hairline)]">
                        <SemanticConstellation
                          ref={constellation}
                          className="absolute inset-0"
                          regions={PILOT_REGIONS}
                          intensity={0.7}
                          interactive={false}
                          showLabels
                        />
                      </div>
                    ) : current.kind === "card" ? (
                      <div className="rounded-xl border border-[var(--cos-nova)]/30 bg-[var(--cos-panel-raised)] p-4 max-w-md">
                        <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--cos-nova)] mr-2" />
                        <span className="text-sm text-[var(--cos-ink)]">{current.body}</span>
                      </div>
                    ) : (
                      <div className="rounded-xl border border-[var(--cos-hairline)] bg-[var(--cos-panel-raised)] p-4 max-w-md">
                        <span className="text-sm text-[var(--cos-ink)]">{current.body}</span>
                      </div>
                    )}
                  </motion.div>
                </AnimatePresence>
              </div>
            </div>
          </MockupFrame>

          {/* scene scrubber + honesty note */}
          <div className="mt-5 flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-2" role="tablist" aria-label="Escenas">
              {scenes.map((s, i) => (
                <button
                  key={i}
                  type="button"
                  role="tab"
                  aria-selected={scene === i}
                  aria-label={s.command}
                  onClick={() => setScene(i)}
                  className={`h-2 rounded-full transition-all duration-300 ${
                    scene === i ? "w-8 bg-[var(--cos-nova)]" : "w-2 bg-[var(--cos-track)]"
                  }`}
                />
              ))}
            </div>
            <p className="text-[11px] text-[var(--cos-faint)]">{t("pilot.honesty")}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
