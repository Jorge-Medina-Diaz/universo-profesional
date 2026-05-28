import { motion } from "motion/react";
import type { ReactNode, CSSProperties } from "react";

const EASE = [0.2, 0.8, 0.2, 1] as const;

export function SectionHeading({
  eyebrow,
  title,
  subtitle,
  align = "center",
  accent = "#6ece9d",
}: {
  eyebrow?: string;
  title: ReactNode;
  subtitle?: ReactNode;
  align?: "center" | "left";
  accent?: string;
}) {
  const alignCls = align === "center" ? "text-center items-center" : "text-left items-start";
  return (
    <div className={`mx-auto flex max-w-2xl flex-col ${alignCls} ${align === "center" ? "" : "mx-0"}`}>
      {eyebrow && (
        <motion.span
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5, ease: EASE }}
          className="cos-eyebrow mb-5"
          style={{ "--accent": accent } as CSSProperties}
        >
          {eyebrow}
        </motion.span>
      )}
      <motion.h2
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-60px" }}
        transition={{ duration: 0.6, ease: EASE }}
        className="cos-display text-[clamp(32px,5vw,56px)] leading-[1.02]"
      >
        {title}
      </motion.h2>
      {subtitle && (
        <motion.p
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.6, delay: 0.1, ease: EASE }}
          className="mt-5 max-w-xl text-[var(--cos-stone)] md:text-lg"
        >
          {subtitle}
        </motion.p>
      )}
    </div>
  );
}
