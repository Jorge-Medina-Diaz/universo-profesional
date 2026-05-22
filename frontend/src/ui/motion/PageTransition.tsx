import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

/**
 * Wraps the current route in a fade transition. The parent must pass a
 * stable `routeKey` (e.g., the current hash path) so AnimatePresence can
 * detect transitions.
 */
export function PageTransition({
  routeKey,
  children,
}: {
  routeKey: string;
  children: ReactNode;
}) {
  const reduced = useReducedMotion();
  if (reduced) return <>{children}</>;

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={routeKey}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.2, ease: [0.2, 0.8, 0.2, 1] }}
        className="h-full"
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
