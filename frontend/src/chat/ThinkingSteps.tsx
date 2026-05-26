/**
 * ThinkingSteps — inline progress indicator for agent reasoning.
 *
 * Renders a vertical list of steps with animated checkmarks. Used both
 * via `useCoAgentStateRender` (real backend state) and as a heuristic
 * fallback while the agent is streaming its first tokens.
 */
import { useMemo } from "react";
import { Check, Loader2 } from "lucide-react";
import { cn } from "@/ui";

export interface ThinkingStep {
  id: string;
  label: string;
  status: "pending" | "active" | "done";
}

interface Props {
  steps: ThinkingStep[];
  className?: string;
}

export function ThinkingSteps({ steps, className }: Props) {
  const visible = useMemo(() => steps.filter((s) => s.status !== "pending"), [steps]);
  if (visible.length === 0) return null;

  return (
    <div className={cn("thinking-steps", className)}>
      {steps.map((step) => {
        const isDone = step.status === "done";
        const isActive = step.status === "active";
        if (!isDone && !isActive) return null;
        return (
          <div
            key={step.id}
            className={cn(
              "thinking-step",
              isDone && "thinking-step--done",
              isActive && "thinking-step--active",
            )}
          >
            <span className="thinking-step__icon">
              {isDone ? (
                <Check size={11} strokeWidth={2.5} />
              ) : (
                <Loader2 size={11} strokeWidth={2.5} className="animate-spin" />
              )}
            </span>
            <span className="thinking-step__label">{step.label}</span>
          </div>
        );
      })}
    </div>
  );
}

/** Heuristic thinking steps derived from the start of an agent reply. */
export function useHeuristicThinkingSteps(text: string, isGenerating: boolean): ThinkingStep[] {
  return useMemo(() => {
    const lower = text.toLowerCase();
    const steps: ThinkingStep[] = [];

    const add = (id: string, label: string, trigger: string) => {
      const idx = lower.indexOf(trigger);
      steps.push({
        id,
        label,
        status: idx >= 0 && idx < 120 ? "done" : idx >= 0 ? "active" : "pending",
      });
    };

    add("analyze", "Analizando tu perfil…", "analiz");
    add("search", "Buscando experiencias relevantes…", "busc");
    add("score", "Calculando match score…", "match");
    add("review", "Revisando recordatorios…", "recordatorio");
    add("sync", "Sincronizando datos…", "sincroniz");
    add("draft", "Redactando respuesta…", "redact");

    // If none matched but we're generating, show a generic "Procesando…" step.
    if (isGenerating && steps.every((s) => s.status === "pending")) {
      steps.unshift({ id: "think", label: "Pensando…", status: "active" });
    }

    return steps;
  }, [text, isGenerating]);
}
