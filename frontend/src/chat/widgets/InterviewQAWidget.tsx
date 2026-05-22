/**
 * InterviewQAWidget — interview prep kit for a specific company/role.
 *
 * Data shape from the interview_prep_specialist:
 *   {
 *     company: string,
 *     role?: string,
 *     questions: [{ question, kind, hint? }],
 *     tips?: string[],
 *     strengths?: string[],
 *     gaps?: string[]
 *   }
 *
 * Q kinds: behavioural | technical | curveball | reverse.
 */
import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  ChevronDown,
  MessageSquare,
  Code2,
  Sparkles,
  Mic,
  Lightbulb,
  Check,
  Minus,
} from "lucide-react";
import { Badge, cn } from "@/ui";

type QKind = "behavioural" | "technical" | "curveball" | "reverse";

interface QA {
  question: string;
  kind?: QKind;
  hint?: string;
}

interface InterviewQAData {
  company?: string;
  role?: string;
  questions?: QA[];
  tips?: string[];
  strengths?: string[];
  gaps?: string[];
}

const KIND_META: Record<
  QKind,
  { label: string; icon: typeof MessageSquare; tone: "leaf" | "sunbeam" | "stone" | "ink" }
> = {
  behavioural: { label: "Behavioural", icon: MessageSquare, tone: "leaf" },
  technical: { label: "Técnica", icon: Code2, tone: "sunbeam" },
  curveball: { label: "Curveball", icon: Sparkles, tone: "stone" },
  reverse: { label: "Tú a ellos", icon: Mic, tone: "ink" },
};

export function InterviewQAWidget({ data }: { data: InterviewQAData }) {
  const questions = data.questions ?? [];
  const [open, setOpen] = useState<Set<number>>(() => new Set([0]));
  const toggle = (i: number) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });

  return (
    <div className="flex flex-col gap-3">
      {(data.strengths?.length || data.gaps?.length) ? (
        <div className="grid grid-cols-2 gap-2">
          {data.strengths?.length ? (
            <div className="rounded-btn bg-leaf-soft px-3 py-2">
              <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-leaf-ink font-medium mb-1">
                <Check size={11} />
                <span>Fortalezas</span>
              </div>
              <ul className="text-xs text-ink/85 leading-snug space-y-0.5">
                {data.strengths.slice(0, 3).map((s, i) => (
                  <li key={i}>· {s}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {data.gaps?.length ? (
            <div className="rounded-btn bg-amber-50 border border-amber-100 px-3 py-2">
              <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-amber-700 font-medium mb-1">
                <Minus size={11} />
                <span>A reforzar</span>
              </div>
              <ul className="text-xs text-ink/85 leading-snug space-y-0.5">
                {data.gaps.slice(0, 3).map((s, i) => (
                  <li key={i}>· {s}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}

      {data.tips?.length ? (
        <div className="rounded-btn bg-canvas border border-ink/[0.08] px-3 py-2">
          <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-stone font-medium mb-1">
            <Lightbulb size={11} />
            <span>Tips para esta entrevista</span>
          </div>
          <ul className="text-xs text-ink/85 leading-snug space-y-1">
            {data.tips.map((t, i) => (
              <li key={i}>· {t}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="flex flex-col gap-1.5">
        <div className="text-[11px] uppercase tracking-wide text-stone font-medium">
          Preguntas posibles ({questions.length})
        </div>
        <ul className="flex flex-col gap-1.5">
          {questions.map((q, i) => {
            const isOpen = open.has(i);
            const kind = q.kind ?? "behavioural";
            const meta = KIND_META[kind] ?? KIND_META.behavioural;
            const Icon = meta.icon;
            return (
              <li
                key={i}
                className="rounded-btn border border-ink/[0.08] overflow-hidden"
              >
                <button
                  type="button"
                  onClick={() => toggle(i)}
                  className="w-full flex items-start justify-between gap-2 px-3 py-2 text-left hover:bg-black/[0.02] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/20 focus-visible:ring-offset-1"
                  aria-expanded={isOpen}
                >
                  <div className="flex items-start gap-2 flex-1 min-w-0">
                    <Badge tone={meta.tone} size="sm" icon={<Icon size={10} />}>
                      {meta.label}
                    </Badge>
                    <span className="text-xs text-ink leading-snug">{q.question}</span>
                  </div>
                  <ChevronDown
                    size={14}
                    className={cn(
                      "text-stone shrink-0 transition-transform duration-180",
                      isOpen && "rotate-180",
                    )}
                  />
                </button>
                <AnimatePresence initial={false}>
                  {isOpen && q.hint ? (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.18 }}
                      className="overflow-hidden bg-canvas/60"
                    >
                      <div className="px-3 pb-2.5 pt-1 text-xs text-ink/75 leading-relaxed border-t border-ink/[0.05]">
                        <span className="text-stone">Tip · </span>
                        {q.hint}
                      </div>
                    </motion.div>
                  ) : null}
                </AnimatePresence>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
