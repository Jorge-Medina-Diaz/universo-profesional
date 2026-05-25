/**
 * FloatingChat — a Claude/Typeform-style composer that floats over the
 * universe constellation and expands into the full chat on focus.
 *
 * The real CopilotKit surface (passed as children) stays mounted the entire
 * time — we only animate the panel's height and toggle a `chat-collapsed`
 * class that hides the message stream when collapsed. This preserves
 * streaming + HITL cards without forwarding messages between two UIs.
 */
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/ui";

export interface FloatingChatProps {
  children: ReactNode;
  onExpandedChange?: (expanded: boolean) => void;
}

export function FloatingChat({ children, onExpandedChange }: FloatingChatProps) {
  const [expanded, setExpanded] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const set = (v: boolean) => {
    setExpanded(v);
    onExpandedChange?.(v);
  };

  useEffect(() => {
    if (!expanded) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") set(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expanded]);

  return (
    <>
      {/* Dim backdrop — click to collapse */}
      <div
        aria-hidden
        onClick={() => set(false)}
        className={cn(
          "fixed inset-0 z-20 bg-ink/25 backdrop-blur-[2px] transition-opacity duration-280 ease-pirsch",
          expanded ? "opacity-100" : "opacity-0 pointer-events-none",
        )}
      />

      {/* Floating panel. Expansion is driven ONLY by focus entering the panel
          (clicking/tapping the composer focuses it) — a broad onClick here used
          to fight the inner controls (attach/send) and the composer. */}
      <div
        ref={panelRef}
        onFocusCapture={() => !expanded && set(true)}
        className={cn(
          "fixed left-1/2 -translate-x-1/2 z-30 w-[calc(100%-2rem)] max-w-3xl",
          "rounded-card border border-hairline bg-canvas/95 backdrop-blur shadow-float",
          "flex flex-col overflow-hidden transition-all duration-420 ease-pirsch",
          expanded
            ? "bottom-20 md:bottom-6 h-[min(76vh,820px)]"
            : "bottom-24 md:bottom-12 h-[88px] cursor-text hover:shadow-lift hover:-translate-y-[1px]",
          !expanded && "chat-collapsed",
        )}
      >
        {expanded && (
          <div className="flex items-center justify-between px-4 py-2 hairline-b shrink-0">
            <span className="eyebrow">Tu universo · chat</span>
            <button
              type="button"
              aria-label="Minimizar chat"
              onClick={(e) => {
                e.stopPropagation();
                set(false);
              }}
              className="grid place-items-center w-7 h-7 rounded-full text-stone hover:text-ink hover:bg-surface/70 transition-colors"
            >
              <ChevronDown size={18} />
            </button>
          </div>
        )}
        <div className="flex-1 min-h-0 chat-surface-area">{children}</div>
      </div>
    </>
  );
}
