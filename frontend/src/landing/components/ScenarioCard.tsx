import type { ReactNode } from "react";
import { motion } from "motion/react";

interface Props {
  icon: ReactNode;
  label: string;
  title: string;
  description: string;
  features: string[];
  className?: string;
}

export function ScenarioCard({ icon, label, title, description, features, className = "" }: Props) {
  return (
    <motion.div
      className={`group relative bg-canvas rounded-2xl border border-ink/[0.06] p-6 md:p-8 hover:border-ink/10 transition-all duration-500 ${className}`}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.5, ease: [0.2, 0.8, 0.2, 1] }}
    >
      {/* Subtle hover glow */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-sunbeam/[0.03] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />

      <div className="relative">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-surface border border-ink/[0.06] flex items-center justify-center text-stone">
            {icon}
          </div>
          <span className="text-[11px] uppercase tracking-[0.15em] text-stone/60 font-medium">
            {label}
          </span>
        </div>

        <h3 className="font-display text-xl md:text-2xl text-ink mb-2">{title}</h3>
        <p className="text-sm text-stone/80 leading-relaxed mb-5">{description}</p>

        <ul className="space-y-2.5">
          {features.map((f, i) => (
            <li key={i} className="flex items-start gap-2.5 text-sm text-ink/70">
              <span className="w-1.5 h-1.5 rounded-full bg-sunbeam/70 mt-1.5 shrink-0" />
              {f}
            </li>
          ))}
        </ul>
      </div>
    </motion.div>
  );
}
