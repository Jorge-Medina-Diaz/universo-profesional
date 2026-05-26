import { useRef, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useEscapeKey } from "@/shared/useEscapeKey";
import { useClickOutside } from "@/shared/useClickOutside";
import { cn } from "./cn";

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
  /** Max width variant */
  size?: "sm" | "md" | "lg";
}

const sizeClasses = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
};

export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  className,
  size = "md",
}: DialogProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  useEscapeKey(onClose, open);
  useClickOutside(contentRef, onClose, open);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          aria-modal="true"
          role="dialog"
        >
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Content */}
          <motion.div
            ref={contentRef}
            className={cn(
              "relative w-full rounded-2xl bg-canvas shadow-xl border border-ink/10",
              sizeClasses[size],
              className,
            )}
            initial={{ scale: 0.96, opacity: 0, y: 8 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.96, opacity: 0, y: 8 }}
            transition={{ type: "spring", damping: 25, stiffness: 320 }}
          >
            {(title || description) && (
              <div className="px-6 pt-6 pb-2">
                {title && (
                  <h2 className="text-lg font-semibold text-ink">{title}</h2>
                )}
                {description && (
                  <p className="mt-1 text-sm text-stone">{description}</p>
                )}
              </div>
            )}
            <div className="px-6 py-4">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
