import { motion, useReducedMotion, type HTMLMotionProps } from "motion/react";
import type { ReactNode } from "react";

export interface ChatMessageMotionProps extends Omit<HTMLMotionProps<"div">, "initial" | "animate"> {
  children: ReactNode;
}

/**
 * Subtle entry for HITL cards and ephemeral chat artefacts.
 * Pirsch-style: slide-up 6px, 240ms.
 */
export function ChatMessageMotion({ children, ...rest }: ChatMessageMotionProps) {
  const reduced = useReducedMotion();
  if (reduced) return <div {...(rest as object)}>{children}</div>;
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: [0.2, 0.8, 0.2, 1] }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}
