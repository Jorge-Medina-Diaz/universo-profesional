import { motion } from "motion/react";

interface Props {
  quote: string;
  author: string;
  role: string;
  metric: string;
  metricLabel: string;
  delay?: number;
}

export function TestimonialCard({
  quote,
  author,
  role,
  metric,
  metricLabel,
  delay = 0,
}: Props) {
  return (
    <motion.div
      className="cos-panel relative flex h-full flex-col p-6 md:p-7"
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.5, delay, ease: [0.2, 0.8, 0.2, 1] }}
    >
      <div className="cos-display mb-3 text-5xl leading-none text-[#ffda6e]/40">&ldquo;</div>
      <p className="mb-6 flex-1 text-[15px] leading-relaxed text-[var(--cos-ink)]">{quote}</p>
      <div className="flex items-center justify-between border-t border-[var(--cos-hairline)] pt-5">
        <div>
          <div className="text-sm font-medium text-[var(--cos-ink)]">{author}</div>
          <div className="text-xs text-[var(--cos-faint)]">{role}</div>
        </div>
        <div className="text-right">
          <div className="cos-display text-lg text-[#00d4aa]">{metric}</div>
          <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--cos-faint)]">
            {metricLabel}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
