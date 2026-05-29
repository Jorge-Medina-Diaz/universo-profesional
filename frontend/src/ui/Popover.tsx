import { useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { useClickOutside } from "@/shared/useClickOutside";
import { cn } from "./cn";

export interface PopoverProps {
  trigger: ReactNode;
  children: ReactNode;
  placement?: "bottom-start" | "bottom-end" | "top-start" | "top-end";
  className?: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

const placementClasses: Record<string, string> = {
  "bottom-start": "left-0 top-full mt-2",
  "bottom-end": "right-0 top-full mt-2",
  "top-start": "left-0 bottom-full mb-2",
  "top-end": "right-0 bottom-full mb-2",
};

export function Popover({
  trigger,
  children,
  placement = "bottom-start",
  className,
  open: controlledOpen,
  onOpenChange,
}: PopoverProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : internalOpen;
  const setOpen = (next: boolean) => {
    if (!isControlled) setInternalOpen(next);
    onOpenChange?.(next);
  };

  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false), open);

  return (
    <div ref={ref} className="relative inline-block">
      <div
        onClick={() => setOpen(!open)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen(!open);
          }
        }}
        role="button"
        tabIndex={0}
        aria-expanded={open}
      >
        {trigger}
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            className={cn(
              "absolute z-40 min-w-[12rem] rounded-xl bg-canvas shadow-lg border border-ink/10 p-1",
              placementClasses[placement],
              className,
            )}
            initial={{ opacity: 0, scale: 0.96, y: -4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -4 }}
            transition={{ type: "spring", damping: 25, stiffness: 320 }}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
