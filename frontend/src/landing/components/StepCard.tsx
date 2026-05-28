import type { ReactNode } from "react";
import { motion } from "motion/react";

interface Props {
  step: number;
  title: string;
  description: string;
  icon: ReactNode;
  delay?: number;
}

export function StepCard({ step, title, description, icon, delay = 0 }: Props) {
  return (
    <motion.div
      className="relative flex gap-5"
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.5, delay, ease: [0.2, 0.8, 0.2, 1] }}
    >
      {/* Number + line */}
      <div className="flex flex-col items-center shrink-0">
        <div className="w-10 h-10 rounded-full bg-surface border border-ink/[0.08] flex items-center justify-center text-sm font-display text-stone">
          {step}
        </div>
        <div className="w-px flex-1 min-h-[24px] bg-ink/8 mt-3" />
      </div>

      <div className="pb-8">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-stone/40">{icon}</span>
          <h4 className="font-display text-base text-ink">{title}</h4>
        </div>
        <p className="text-sm text-stone/70 leading-relaxed">{description}</p>
      </div>
    </motion.div>
  );
}
