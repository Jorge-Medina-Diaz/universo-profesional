/**
 * Lightweight guided tour — spotlight + tooltip stepping through targeted
 * elements. Each target is found by `data-tour="<id>"` attribute so we can
 * keep the tour decoupled from the actual JSX (no portal refs needed).
 *
 * Usage:
 *   <span data-tour="universe-nav">...</span>
 *   tour.start("first-run")  // or auto-start on first visit
 */
import {
  useCallback,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { AnimatePresence, motion } from "motion/react";
import { ArrowRight, X, Sparkles, Check } from "lucide-react";
import { Button, cn } from "@/ui";

export interface TourStep {
  id: string;
  /** `data-tour` attribute or CSS selector. Empty = floating modal centered. */
  target?: string;
  title: string;
  body: ReactNode;
  /** Side of the target to anchor the tooltip. */
  placement?: "top" | "bottom" | "left" | "right" | "center";
  /** Optional CTA in the tooltip (e.g. "Try it"). */
  cta?: { label: string; onClick: () => void };
}

export interface TourDefinition {
  id: string;
  steps: TourStep[];
}

interface TourState {
  active: TourDefinition | null;
  stepIndex: number;
}

const STORAGE_KEY = "cvs-saas-tours-completed";

function loadCompleted(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    return new Set(JSON.parse(raw) as string[]);
  } catch {
    return new Set();
  }
}

function saveCompleted(set: Set<string>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(set)));
  } catch {
    /* ignore */
  }
}

let externalStart: ((tour: TourDefinition) => void) | null = null;
let externalIsCompleted: ((tourId: string) => boolean) | null = null;

/** Imperative entry points usable outside React. */
export const tour = {
  start: (def: TourDefinition) => externalStart?.(def),
  isCompleted: (id: string) => externalIsCompleted?.(id) ?? false,
};

export function TourProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<TourState>({ active: null, stepIndex: 0 });
  const [completed, setCompleted] = useState<Set<string>>(() => loadCompleted());

  const start = useCallback((tourDef: TourDefinition) => {
    setState({ active: tourDef, stepIndex: 0 });
  }, []);

  const close = useCallback(
    (tourId?: string) => {
      setState({ active: null, stepIndex: 0 });
      if (tourId) {
        setCompleted((prev) => {
          const next = new Set(prev);
          next.add(tourId);
          saveCompleted(next);
          return next;
        });
      }
    },
    [],
  );

  const next = useCallback(() => {
    setState((s) => {
      if (!s.active) return s;
      const isLast = s.stepIndex >= s.active.steps.length - 1;
      if (isLast) {
        close(s.active.id);
        return { active: null, stepIndex: 0 };
      }
      return { ...s, stepIndex: s.stepIndex + 1 };
    });
  }, [close]);

  const prev = useCallback(() => {
    setState((s) => ({ ...s, stepIndex: Math.max(0, s.stepIndex - 1) }));
  }, []);

  const skip = useCallback(() => {
    setState((s) => {
      if (s.active) close(s.active.id);
      return { active: null, stepIndex: 0 };
    });
  }, [close]);

  const isCompleted = useCallback(
    (id: string) => completed.has(id),
    [completed],
  );

  useEffect(() => {
    externalStart = start;
    externalIsCompleted = isCompleted;
    return () => {
      if (externalStart === start) externalStart = null;
      if (externalIsCompleted === isCompleted) externalIsCompleted = null;
    };
  }, [start, isCompleted]);

  return (
    <>
      {children}
      <TourOverlay state={state} onNext={next} onPrev={prev} onSkip={skip} />
    </>
  );
}

function TourOverlay({
  state,
  onNext,
  onPrev,
  onSkip,
}: {
  state: TourState;
  onNext: () => void;
  onPrev: () => void;
  onSkip: () => void;
}) {
  const step = state.active ? state.active.steps[state.stepIndex] : null;
  const total = state.active?.steps.length ?? 0;
  const targetRect = useTargetRect(step?.target);

  useEffect(() => {
    if (!state.active) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onSkip();
      } else if (e.key === "ArrowRight" || e.key === "Enter") {
        e.preventDefault();
        onNext();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        onPrev();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [state.active, onNext, onPrev, onSkip]);

  return (
    <AnimatePresence>
      {step && (
        <>
          <Spotlight rect={targetRect} placement={step.placement} />
          <Tooltip
            step={step}
            stepIndex={state.stepIndex}
            total={total}
            rect={targetRect}
            onNext={onNext}
            onPrev={onPrev}
            onSkip={onSkip}
          />
        </>
      )}
    </AnimatePresence>
  );
}

function Spotlight({
  rect,
  placement,
}: {
  rect: DOMRect | null;
  placement?: TourStep["placement"];
}) {
  // Center / no target → full backdrop blur.
  if (!rect || placement === "center") {
    return (
      <motion.div
        key="backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="fixed inset-0 z-[55] bg-ink/45 backdrop-blur-sm"
      />
    );
  }
  const pad = 8;
  const x = rect.left - pad;
  const y = rect.top - pad;
  const w = rect.width + pad * 2;
  const h = rect.height + pad * 2;
  return (
    <motion.svg
      key="spotlight"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.22 }}
      className="fixed inset-0 z-[55] pointer-events-none"
      width="100%"
      height="100%"
      aria-hidden
    >
      <defs>
        <mask id="tour-cutout">
          <rect width="100%" height="100%" fill="white" />
          <motion.rect
            initial={false}
            animate={{ x, y, width: w, height: h, rx: 14 }}
            transition={{ duration: 0.32, ease: [0.2, 0.8, 0.2, 1] }}
            fill="black"
          />
        </mask>
      </defs>
      <rect
        width="100%"
        height="100%"
        fill="rgba(10,10,10,0.55)"
        mask="url(#tour-cutout)"
      />
      <motion.rect
        initial={false}
        animate={{ x, y, width: w, height: h, rx: 14 }}
        transition={{ duration: 0.32, ease: [0.2, 0.8, 0.2, 1] }}
        fill="none"
        stroke="var(--color-leafy-green)"
        strokeWidth="2"
      />
    </motion.svg>
  );
}

function Tooltip({
  step,
  stepIndex,
  total,
  rect,
  onNext,
  onPrev,
  onSkip,
}: {
  step: TourStep;
  stepIndex: number;
  total: number;
  rect: DOMRect | null;
  onNext: () => void;
  onPrev: () => void;
  onSkip: () => void;
}) {
  const isLast = stepIndex >= total - 1;
  const isFirst = stepIndex === 0;
  const isCentered = !rect || step.placement === "center";
  const style = isCentered ? undefined : computeAnchor(rect!, step.placement ?? "bottom");

  return (
    <motion.div
      key={`tooltip-${step.id}`}
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 6, scale: 0.97 }}
      transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
      className={cn(
        "fixed z-[56] w-[360px] max-w-[calc(100vw-2rem)] rounded-card bg-canvas shadow-lift border border-ink/8 overflow-hidden",
        isCentered && "left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2",
      )}
      style={style}
      role="dialog"
      aria-labelledby={`tour-${step.id}-title`}
    >
      <div className="px-5 pt-5 pb-4 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-medium text-stone uppercase tracking-wider">
            <Sparkles size={12} className="text-leaf-ink" />
            <span>
              {stepIndex + 1} / {total}
            </span>
          </div>
          <button
            type="button"
            onClick={onSkip}
            aria-label="Saltar tour"
            className="w-7 h-7 inline-flex items-center justify-center rounded-full text-stone hover:text-ink hover:bg-black/[0.04] transition-colors duration-180"
          >
            <X size={14} />
          </button>
        </div>
        <h3
          id={`tour-${step.id}-title`}
          className="text-heading-sm font-medium tracking-tight text-ink leading-tight"
        >
          {step.title}
        </h3>
        <div className="text-sm text-stone leading-relaxed">{step.body}</div>
      </div>
      <div className="flex items-center justify-between gap-2 px-5 py-3 bg-surface border-t border-ink/5">
        <Progress total={total} index={stepIndex} />
        <div className="flex items-center gap-2">
          {!isFirst && (
            <Button size="sm" variant="ghost" onClick={onPrev}>
              Atrás
            </Button>
          )}
          {step.cta && (
            <Button size="sm" variant="outline" onClick={step.cta.onClick}>
              {step.cta.label}
            </Button>
          )}
          <Button
            size="sm"
            onClick={onNext}
            trailingIcon={isLast ? <Check size={14} /> : <ArrowRight size={14} />}
          >
            {isLast ? "Listo" : "Siguiente"}
          </Button>
        </div>
      </div>
    </motion.div>
  );
}

function Progress({ total, index }: { total: number; index: number }) {
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: total }).map((_, i) => (
        <span
          key={i}
          aria-hidden
          className={cn(
            "h-1.5 rounded-full transition-all duration-280 ease-pirsch",
            i === index
              ? "w-6 bg-leaf"
              : i < index
                ? "w-1.5 bg-leaf"
                : "w-1.5 bg-ink/15",
          )}
        />
      ))}
    </div>
  );
}

function computeAnchor(rect: DOMRect, placement: NonNullable<TourStep["placement"]>) {
  const W = 360;
  const margin = 14;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  switch (placement) {
    case "top": {
      const left = clamp(rect.left + rect.width / 2 - W / 2, margin, vw - W - margin);
      const top = Math.max(margin, rect.top - 200);
      return { left, top };
    }
    case "left": {
      const left = Math.max(margin, rect.left - W - margin);
      const top = clamp(rect.top + rect.height / 2 - 80, margin, vh - 200);
      return { left, top };
    }
    case "right": {
      const left = Math.min(vw - W - margin, rect.right + margin);
      const top = clamp(rect.top + rect.height / 2 - 80, margin, vh - 200);
      return { left, top };
    }
    case "bottom":
    default: {
      const left = clamp(rect.left + rect.width / 2 - W / 2, margin, vw - W - margin);
      const top = Math.min(vh - 200, rect.bottom + margin);
      return { left, top };
    }
  }
}

function clamp(v: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, v));
}

function useTargetRect(selector?: string): DOMRect | null {
  const [rect, setRect] = useState<DOMRect | null>(null);
  useEffect(() => {
    if (!selector) {
      setRect(null);
      return;
    }
    const isAttr = !selector.startsWith(".") && !selector.startsWith("#");
    const cssSelector = isAttr ? `[data-tour="${selector}"]` : selector;
    const measure = () => {
      const el = document.querySelector(cssSelector) as HTMLElement | null;
      if (!el) {
        setRect(null);
        return;
      }
      const r = el.getBoundingClientRect();
      setRect(r);
      el.scrollIntoView({ block: "center", behavior: "smooth" });
    };
    measure();
    const t = window.setInterval(measure, 250);
    window.addEventListener("resize", measure);
    return () => {
      window.clearInterval(t);
      window.removeEventListener("resize", measure);
    };
  }, [selector]);
  return rect;
}
