/**
 * Long-running task progress card. Display-only — the agent passes the steps
 * + current state and we render the spinner/check icons.
 *
 * Sprint B scope: the steps are static (agent emits one ProgressCard per
 * progression step). Sprint C will hook this to live SSE/poll feeds.
 */
import { Loader2, Send, X } from "lucide-react";
import { Badge, ChatMessageMotion, ProgressSteps, cn, type ProgressStep } from "@/ui";

export interface ProgressCardProps {
  title: string;
  /** "running" while at least one step is active; "done" when all done; "error" if any failed */
  state: "running" | "done" | "error";
  steps: ProgressStep[];
  detail?: string;
  errorMessage?: string;
  /** Optional close handler. Renders an "×" button in the header. The card
   *  goes away but the underlying task is NOT aborted server-side. */
  onDismiss?: () => void;
  /** Label for the dismiss button. Defaults to "Cerrar" for finished tasks
   *  and "Ocultar" for in-flight ones (since we're not actually cancelling). */
  dismissLabel?: string;
}

export function ProgressCard({
  title,
  state,
  steps,
  detail,
  errorMessage,
  onDismiss,
  dismissLabel,
}: ProgressCardProps) {
  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface p-5 my-3 max-w-md border border-ink/[0.06] shadow-soft">
        <header className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-start gap-3">
            <span
              aria-hidden
              className={cn(
                "inline-flex items-center justify-center w-9 h-9 rounded-full shrink-0",
                state === "done" && "bg-leaf-soft text-leaf-ink",
                state === "error" && "bg-danger-soft text-danger-ink",
                state === "running" && "bg-sunbeam-soft text-sunbeam-ink",
              )}
            >
              {state === "running" ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Send size={14} />
              )}
            </span>
            <div className="min-w-0 space-y-1">
              <h4 className="font-medium text-sm text-ink leading-tight">{title}</h4>
              {detail && <p className="text-xs text-stone">{detail}</p>}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Badge
              tone={state === "done" ? "leaf" : state === "error" ? "danger" : "sunbeam"}
              size="sm"
            >
              {state === "done" ? "Completado" : state === "error" ? "Error" : "En curso"}
            </Badge>
            {onDismiss && (
              <button
                type="button"
                onClick={onDismiss}
                aria-label={dismissLabel ?? "Cerrar"}
                title={
                  dismissLabel ??
                  (state === "running"
                    ? "Ocultar (la tarea sigue en segundo plano)"
                    : "Cerrar")
                }
                className="w-7 h-7 inline-flex items-center justify-center rounded-full text-stone hover:text-ink hover:bg-ink/[0.04] transition-colors"
              >
                <X size={12} />
              </button>
            )}
          </div>
        </header>
        <ProgressSteps steps={steps} />
        {errorMessage && (
          <div className="mt-3 rounded-card bg-danger-soft border border-danger/30 text-danger-ink text-xs px-3 py-2">
            {errorMessage}
          </div>
        )}
      </div>
    </ChatMessageMotion>
  );
}
