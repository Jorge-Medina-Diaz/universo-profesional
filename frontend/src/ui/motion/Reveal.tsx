import { motion, useReducedMotion, type HTMLMotionProps } from "motion/react";
import type { ReactNode } from "react";

export interface RevealProps extends Omit<HTMLMotionProps<"div">, "initial" | "animate" | "transition"> {
  delay?: number;
  y?: number;
  duration?: number;
  once?: boolean;
  children: ReactNode;
}

/**
 * Fade-up enter animation. Pirsch-style: subtle (8px), short (280ms),
 * with a soft custom easeOut. Respects prefers-reduced-motion.
 */
export function Reveal({
  delay = 0,
  y = 8,
  duration = 0.28,
  once = true,
  children,
  ...rest
}: RevealProps) {
  const reduced = useReducedMotion();
  if (reduced) {
    return <div {...(rest as object)}>{children}</div>;
  }
  return (
    <motion.div
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once, amount: 0.2 }}
      transition={{ duration, delay, ease: [0.2, 0.8, 0.2, 1] }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}
