/**
 * FloatingChat — a Claude/Typeform-style composer that floats over the
 * universe constellation and expands into the full chat on focus.
 *
 * The real CopilotKit surface (passed as children) stays mounted the entire
 * time — we only animate the panel's height and toggle a `chat-collapsed`
 * class that hides the message stream when collapsed. This preserves
 * streaming + HITL cards without forwarding messages between two UIs.
 */
import { useRef, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { useEscapeKey } from "@/shared/useEscapeKey";
import { cn } from "@/ui";
import { useChatState } from "@/chat/state";

export interface FloatingChatProps {
  children: ReactNode;
  onExpandedChange?: (expanded: boolean) => void;
}

export function FloatingChat({ children, onExpandedChange }: FloatingChatProps) {
  const expanded = useChatState((s) => s.chatExpanded);
  const setExpanded = useChatState((s) => s.setChatExpanded);
  // Live agent status (written by CopilotSurface from the AG-UI shared state).
  // Null when idle — the chip disappears entirely.
  const agentActivity = useChatState((s) => s.agentActivity);
  const panelRef = useRef<HTMLDivElement>(null);

  const set = (v: boolean) => {
    setExpanded(v);
    onExpandedChange?.(v);
  };

  useEscapeKey(() => set(false), expanded);

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
          "rounded-card border border-hairline bg-[color-mix(in_srgb,var(--surface-canvas)_85%,transparent)] backdrop-blur-md shadow-float",
          "flex flex-col overflow-hidden transition-all duration-420 ease-pirsch",
          expanded
            ? "bottom-20 md:bottom-6 h-[min(76vh,820px)]"
            : "bottom-24 md:bottom-12 h-[88px] cursor-text hover:shadow-lift hover:-translate-y-[1px]",
          !expanded && "chat-collapsed",
        )}
      >
        {/* Collapsed-dock status chip — the agent is visibly "alive" even with
            the panel folded. Reuses the thinking-dots pulse styling. */}
        {!expanded && agentActivity && (
          <div
            aria-live="polite"
            className="pointer-events-none absolute top-2 right-3 z-10 flex max-w-[60%] items-center gap-1.5 rounded-full border border-hairline bg-surface/90 px-2.5 py-1 text-[11px] text-stone backdrop-blur-sm"
          >
            <span className="thinking-dots shrink-0">
              <i /> <i /> <i />
            </span>
            <span className="truncate">{agentActivity.label}</span>
          </div>
        )}
        {expanded && (
          <div className="flex items-center justify-between px-4 py-2 hairline-b shrink-0">
            <span className="flex min-w-0 items-center gap-3">
              <span className="eyebrow shrink-0">Tu universo · chat</span>
              {agentActivity && (
                <span
                  aria-live="polite"
                  className="flex min-w-0 items-center gap-1.5 text-[11px] text-stone"
                >
                  <span className="thinking-dots shrink-0">
                    <i /> <i /> <i />
                  </span>
                  <span className="truncate">{agentActivity.label}</span>
                </span>
              )}
            </span>
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
