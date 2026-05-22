import { motion, useReducedMotion, type HTMLMotionProps } from "motion/react";
import { Children, isValidElement, type ReactNode } from "react";

export interface StaggerProps extends Omit<HTMLMotionProps<"div">, "initial" | "animate" | "variants"> {
  delayStep?: number;
  initialDelay?: number;
  y?: number;
  duration?: number;
  children: ReactNode;
}

/**
 * Stagger wraps each direct child in a synchronized fade-up animation.
 * Use for navigation rows, card grids, shortcut lists.
 */
export function Stagger({
  delayStep = 0.05,
  initialDelay = 0,
  y = 8,
  duration = 0.28,
  className,
  children,
  ...rest
}: StaggerProps) {
  const reduced = useReducedMotion();
  const items = Children.toArray(children);

  if (reduced) {
    return (
      <div className={className} {...(rest as object)}>
        {children}
      </div>
    );
  }

  return (
    <motion.div className={className} initial="hidden" animate="visible" {...rest}>
      {items.map((child, index) => (
        <motion.div
          key={isValidElement(child) && child.key != null ? child.key : index}
          variants={{
            hidden: { opacity: 0, y },
            visible: {
              opacity: 1,
              y: 0,
              transition: {
                duration,
                delay: initialDelay + index * delayStep,
                ease: [0.2, 0.8, 0.2, 1],
              },
            },
          }}
        >
          {child}
        </motion.div>
      ))}
    </motion.div>
  );
}
