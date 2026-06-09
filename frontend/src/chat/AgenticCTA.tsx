/**
 * AgenticCTA — the "do it with the agent" banner that makes the conversational
 * agent the PRIMARY path on a page, demoting the manual form to an advanced
 * fallback. Clicking opens the global agent dock and seeds a contextual prompt
 * so the agent drives the change through its HITL cards (propose_* / present_*),
 * instead of the user filling a non-agentic form.
 *
 * Part of the "kill the basic chat" doctrine: a page may DISPLAY state, but the
 * inviting, default mutation path is agentic.
 */
import { Sparkles, ArrowRight } from "lucide-react";
import { useChatState } from "./state";

export interface AgenticCTAProps {
  /** Headline, e.g. "Ajusta tus preferencias conmigo". */
  title: string;
  /** One-line subtitle describing what the agent will do. */
  subtitle?: string;
  /** The prompt seeded into the chat (becomes the user's opening turn). */
  prompt: string;
  /** Button label. */
  cta?: string;
}

export function AgenticCTA({ title, subtitle, prompt, cta = "Hazlo conmigo" }: AgenticCTAProps) {
  const open = () => {
    useChatState.getState().setPendingInjection({ content: prompt });
    useChatState.getState().setChatExpanded(true);
  };
  return (
    <button
      type="button"
      onClick={open}
      className="group flex w-full items-center gap-3 rounded-card border border-hairline bg-surface px-4 py-3 text-left shadow-soft transition-colors hover:border-ink/20 hover:bg-canvas focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/20"
    >
      <span
        aria-hidden
        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-nova-soft text-nova-ink"
      >
        <Sparkles size={16} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium leading-tight text-ink">{title}</span>
        {subtitle && <span className="mt-0.5 block text-xs text-stone">{subtitle}</span>}
      </span>
      <span className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-ink/70 transition-transform group-hover:translate-x-0.5">
        {cta}
        <ArrowRight size={13} />
      </span>
    </button>
  );
}
