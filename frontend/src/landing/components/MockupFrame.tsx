import type { ReactNode } from "react";
import { motion } from "motion/react";

interface Props {
  children: ReactNode;
  className?: string;
  dark?: boolean;
}

export function MockupFrame({ children, className = "", dark = false }: Props) {
  return (
    <motion.div
      className={`relative rounded-2xl overflow-hidden ${className}`}
      initial={{ y: 20, opacity: 0 }}
      whileInView={{ y: 0, opacity: 1 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.6, ease: [0.2, 0.8, 0.2, 1] }}
    >
      {/* Top bar */}
      <div
        className={`flex items-center gap-2 px-4 py-2.5 border-b ${
          dark
            ? "bg-ink-raised border-canvas/10"
            : "bg-canvas border-ink/[0.06]"
        }`}
      >
        <div className="flex gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-400/70" />
          <span className="w-2.5 h-2.5 rounded-full bg-yellow-400/70" />
          <span className="w-2.5 h-2.5 rounded-full bg-green-400/70" />
        </div>
      </div>
      {/* Content */}
      <div
        className={`${dark ? "bg-ink text-canvas/80" : "bg-canvas text-ink/80"}`}
      >
        {children}
      </div>
      {/* Reflection/shadow */}
      <div className="absolute -inset-x-8 -bottom-8 h-16 bg-ink/5 blur-2xl rounded-full pointer-events-none" />
    </motion.div>
  );
}
