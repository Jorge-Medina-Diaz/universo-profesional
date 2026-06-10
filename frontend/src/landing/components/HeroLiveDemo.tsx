import { useEffect, useRef, useState } from "react";
import { AnimatePresence } from "motion/react";
import { useTranslation } from "react-i18next";

import {
  AgentMsg,
  LandingNudgeChip,
  LandingProposalCard,
  UserMsg,
} from "@/landing/components/cards";
import {
  SemanticConstellation,
  type ConstellationHandle,
  type ConstellationRegion,
} from "@/landing/components/SemanticConstellation";

const STEP_MS = [2200, 2600, 2200, 3000, 3400, 3000, 4200] as const;
const TOTAL_STEPS = STEP_MS.length;

const MEMORY_REGIONS: ConstellationRegion[] = [
  { id: "exp", label: "", color: "#ffda6e", cx: 0.5, cy: 0.28, count: 4, spread: 0.16 },
  { id: "skill", label: "", color: "#6ece9d", cx: 0.32, cy: 0.66, count: 4, spread: 0.14 },
  { id: "proj", label: "", color: "#00d4aa", cx: 0.72, cy: 0.62, count: 3, spread: 0.13 },
];

/**
 * The hero IS the product — and the interaction model IS the canonical one:
 * the USER initiates ("monté un ecommerce"), the agent reacts with specific
 * interest, OFFERS to investigate (the repo), gracefully accepts "no",
 * pulls the thread with OPEN questions, then synthesizes into a proposal
 * and closes with an inviting nudge. Faithful simulation — the live proof
 * is the twin section below.
 */
export function HeroLiveDemo() {
  const { t } = useTranslation("landing");
  const [step, setStep] = useState(0);
  const [cycle, setCycle] = useState(0);
  const [memory, setMemory] = useState({ nodes: 0, edges: 0 });
  const constellation = useRef<ConstellationHandle>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const reduced =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    if (reduced) {
      setStep(TOTAL_STEPS - 1);
      return;
    }
    const timer = window.setTimeout(() => {
      if (step >= TOTAL_STEPS - 1) {
        setStep(0);
        setCycle((c) => c + 1);
      } else {
        setStep(step + 1);
      }
    }, STEP_MS[step]);
    return () => window.clearTimeout(timer);
  }, [step, reduced]);

  // memory grows exactly when the synthesis lands (step 5: proposal confirmed)
  useEffect(() => {
    if (step === 5) {
      constellation.current?.pulseFrom(0.1, 0.9, "proj");
      window.setTimeout(() => constellation.current?.pulseFrom(0.1, 0.9, "skill"), 420);
    }
  }, [step]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [step]);

  return (
    <div className="relative rounded-3xl border border-[var(--cos-hairline)] bg-[rgba(11,13,16,0.72)] backdrop-blur-md overflow-hidden shadow-[0_30px_90px_-30px_rgba(0,0,0,0.8)]">
      {/* window chrome */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[var(--cos-hairline)]">
        <div className="flex items-center gap-1.5">
          <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-white/12" />
          <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-white/12" />
          <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-white/12" />
        </div>
        <span className="text-[10px] font-mono text-[var(--cos-faint)]">{t("hero.demoLabel")}</span>
      </div>

      <div className="grid md:grid-cols-[1fr_180px]">
        {/* the conversation — user first, always */}
        <div
          ref={scrollRef}
          className="flex flex-col gap-2.5 p-4 h-[400px] md:h-[440px] overflow-hidden"
          key={cycle}
        >
          <UserMsg>{t("hero.demo.u1")}</UserMsg>
          {step >= 1 && <AgentMsg>{t("hero.demo.a1")}</AgentMsg>}
          {step >= 2 && <UserMsg>{t("hero.demo.u2")}</UserMsg>}
          {step >= 3 && <AgentMsg>{t("hero.demo.a2")}</AgentMsg>}
          {step >= 4 && <UserMsg>{t("hero.demo.u3")}</UserMsg>}
          {step >= 5 && (
            <LandingProposalCard
              kind="project"
              title={t("hero.demo.proposalTitle")}
              confidence="Alta"
              fields={[
                [t("hero.demo.p1"), "Next.js · Stripe · IA generativa"],
                [t("hero.demo.p2"), t("hero.demo.p2v")],
              ]}
              confirmed={step >= 6}
            />
          )}
          <AnimatePresence>
            {step >= 6 && (
              <div className="mt-1">
                <LandingNudgeChip label={t("hero.demo.nudge")} />
              </div>
            )}
          </AnimatePresence>
        </div>

        {/* the memory panel */}
        <div className="relative border-t md:border-t-0 md:border-l border-[var(--cos-hairline)] min-h-[140px]">
          <SemanticConstellation
            ref={constellation}
            className="absolute inset-0"
            regions={MEMORY_REGIONS}
            intensity={0.6}
            interactive={false}
            showLabels={false}
            onStats={(nodes, edges) => setMemory({ nodes, edges })}
          />
          <div className="absolute bottom-2.5 inset-x-0 text-center">
            <p className="text-[10px] font-mono text-[var(--cos-faint)]">
              {t("hero.counter", { nodes: memory.nodes, edges: memory.edges })}
            </p>
          </div>
        </div>
      </div>

      {/* scrubber */}
      <div
        className="flex items-center gap-1.5 px-4 py-2.5 border-t border-[var(--cos-hairline)]"
        role="tablist"
        aria-label="Demo"
      >
        {Array.from({ length: TOTAL_STEPS }, (_, i) => (
          <button
            key={i}
            type="button"
            role="tab"
            aria-selected={step === i}
            aria-label={`Paso ${i + 1}`}
            onClick={() => setStep(i)}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              step >= i ? "bg-[#00d4aa]" : "bg-[var(--cos-track)]"
            } ${step === i ? "w-7" : "w-3"}`}
          />
        ))}
        <span className="ml-auto text-[10px] text-[var(--cos-faint)]">{t("hero.demoHonesty")}</span>
      </div>
    </div>
  );
}
