/**
 * WidgetShell — common chrome for every widget rendered in the WidgetPane.
 *
 * Header: title + pin/unpin + close.
 * Body: arbitrary children with consistent padding.
 *
 * Animation: fade-up on mount via `motion/react`. We don't use Reveal here
 * because `whileInView` waits for visibility intersection; new widgets that
 * arrive while the pane is already scrolled past would never animate.
 */
import { motion } from "motion/react";
import { Pin, PinOff, X } from "lucide-react";
import type { ReactNode } from "react";
import type { ChatWidget } from "@/chat/state";
import { cn } from "@/ui";

interface WidgetShellProps {
  widget: ChatWidget;
  onRemove: (id: string) => void;
  onTogglePin: (id: string) => void;
  children: ReactNode;
  className?: string;
}

export function WidgetShell({
  widget,
  onRemove,
  onTogglePin,
  children,
  className,
}: WidgetShellProps) {
  return (
    <motion.section
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
      className={cn(
        "group rounded-card border border-ink/8 bg-canvas/85 backdrop-blur-sm shadow-soft overflow-hidden",
        widget.pinned && "border-ink/15 shadow-lift",
        className,
      )}
      aria-label={widget.title}
    >
      <header className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-ink/5">
        <h3 className="text-sm font-medium text-ink leading-tight truncate">
          {widget.title}
        </h3>
        <div className="flex items-center gap-0.5 shrink-0">
          <button
            type="button"
            onClick={() => onTogglePin(widget.id)}
            className={cn(
              "w-7 h-7 rounded-full grid place-items-center text-stone hover:text-ink hover:bg-ink/[0.04] transition-colors focus-visible:ring-2 focus-visible:ring-ink/20 focus-visible:ring-offset-1 focus-visible:outline-none",
              widget.pinned && "text-ink",
            )}
            aria-label={widget.pinned ? "Quitar anclaje" : "Anclar widget"}
            aria-pressed={widget.pinned ?? false}
            title={widget.pinned ? "Anclado" : "Anclar"}
          >
            {widget.pinned ? <PinOff size={14} /> : <Pin size={14} />}
          </button>
          <button
            type="button"
            onClick={() => onRemove(widget.id)}
            className="w-7 h-7 rounded-full grid place-items-center text-stone hover:text-ink hover:bg-ink/[0.04] transition-colors focus-visible:ring-2 focus-visible:ring-ink/20 focus-visible:ring-offset-1 focus-visible:outline-none"
            aria-label="Cerrar widget"
          >
            <X size={14} />
          </button>
        </div>
      </header>
      <div className="p-4">{children}</div>
    </motion.section>
  );
}
