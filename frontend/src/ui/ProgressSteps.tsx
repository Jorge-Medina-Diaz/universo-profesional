import { motion, useReducedMotion } from "motion/react";
import { Check } from "lucide-react";
import { cn } from "./cn";

export type ProgressStepStatus = "pending" | "active" | "done" | "error";

export interface ProgressStep {
  id: string;
  label: string;
  hint?: string;
  status: ProgressStepStatus;
}

export interface ProgressStepsProps {
  steps: ProgressStep[];
  orientation?: "vertical" | "horizontal";
  className?: string;
}

/**
 * Pirsch-style step indicator. Use to communicate slow async flows
 * (LinkedIn Bright Data 30-90s, CV gen pipeline, etc.) without leaving
 * the user staring at a spinner.
 */
export function ProgressSteps({
  steps,
  orientation = "vertical",
  className,
}: ProgressStepsProps) {
  const reduced = useReducedMotion();
  if (orientation === "horizontal") {
    return (
      <ol className={cn("flex items-center gap-2 flex-wrap", className)}>
        {steps.map((s, i) => (
          <li key={s.id} className="flex items-center gap-2 flex-1 min-w-0">
            <StepDot status={s.status} reduced={!!reduced} index={i} compact />
            <span
              className={cn(
                "text-xs truncate",
                s.status === "active" ? "text-ink font-medium" : "text-stone",
              )}
            >
              {s.label}
            </span>
            {i < steps.length - 1 && (
              <span
                aria-hidden
                className={cn(
                  "h-px flex-1 transition-colors duration-280",
                  s.status === "done" ? "bg-leaf" : "bg-ink/10",
                )}
              />
            )}
          </li>
        ))}
      </ol>
    );
  }
  return (
    <ol className={cn("flex flex-col gap-3", className)}>
      {steps.map((s, i) => (
        <li key={s.id} className="flex items-start gap-3">
          <div className="relative shrink-0">
            <StepDot status={s.status} reduced={!!reduced} index={i} />
            {i < steps.length - 1 && (
              <span
                aria-hidden
                className={cn(
                  "absolute left-1/2 -translate-x-1/2 top-7 w-px h-[calc(100%+0.25rem)] transition-colors duration-280",
                  s.status === "done" ? "bg-leaf" : "bg-ink/10",
                )}
              />
            )}
          </div>
          <div className="min-w-0 -mt-0.5 pb-2">
            <div
              className={cn(
                "text-sm leading-tight",
                s.status === "active" ? "text-ink font-medium" : "text-ink",
                s.status === "pending" && "text-stone",
                s.status === "error" && "text-red-700 font-medium",
              )}
            >
              {s.label}
            </div>
            {s.hint && (
              <div className="text-xs text-stone mt-0.5 leading-relaxed">{s.hint}</div>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

function StepDot({
  status,
  reduced,
  index,
  compact,
}: {
  status: ProgressStepStatus;
  reduced: boolean;
  index: number;
  compact?: boolean;
}) {
  const size = compact ? "w-5 h-5" : "w-6 h-6";
  if (status === "done") {
    return (
      <span
        aria-label="Completado"
        className={cn(
          size,
          "inline-flex items-center justify-center rounded-full bg-leaf text-ink shrink-0",
        )}
      >
        <Check size={compact ? 10 : 12} strokeWidth={2.8} />
      </span>
    );
  }
  if (status === "error") {
    return (
      <span
        aria-label="Error"
        className={cn(
          size,
          "inline-flex items-center justify-center rounded-full bg-red-100 text-red-700 shrink-0",
        )}
      >
        <span className="font-bold text-[10px]">!</span>
      </span>
    );
  }
  if (status === "active") {
    return (
      <span
        aria-label="En curso"
        className={cn(
          size,
          "relative inline-flex items-center justify-center rounded-full bg-leaf-soft shrink-0",
        )}
      >
        {!reduced && (
          <motion.span
            animate={{ scale: [1, 1.5, 1], opacity: [0.6, 0, 0.6] }}
            transition={{
              duration: 1.8,
              repeat: Infinity,
              ease: "easeInOut",
              delay: index * 0.12,
            }}
            className="absolute inset-0 rounded-full bg-leaf/40"
          />
        )}
        <span className={cn("relative rounded-full bg-leaf-ink", compact ? "w-1.5 h-1.5" : "w-2 h-2")} />
      </span>
    );
  }
  return (
    <span
      aria-label="Pendiente"
      className={cn(
        size,
        "inline-flex items-center justify-center rounded-full border-2 border-ink/10 bg-canvas shrink-0",
      )}
    />
  );
}
