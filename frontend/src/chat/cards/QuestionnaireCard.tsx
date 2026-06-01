/**
 * A2UI-style batch card — the agent presents 3-5 related questions at once.
 *
 * Supported question kinds:
 *  - single_choice — radio
 *  - multi_choice  — checkbox (returns an array)
 *  - scale         — slider 1..N (default 1..5)
 *  - open          — textarea
 *
 * Submit returns `{ answers: { [qid]: value } }` to the agent via `respond`.
 */
import { useState } from "react";
import { Button, Textarea, ChatMessageMotion, cn } from "@/ui";

export interface QuestionnaireQuestion {
  id: string;
  kind: "single_choice" | "multi_choice" | "scale" | "open";
  // Canonical is `prompt`, but the model frequently emits `question` (and
  // sometimes `label`/`text`/`title`). Accept all so the question text never
  // renders blank.
  prompt?: string;
  question?: string;
  label?: string;
  text?: string;
  title?: string;
  // The agent may emit plain strings OR { label, value } objects — both are
  // normalised at render so an object never reaches React as a child.
  options?: Array<string | { label?: string; value?: string }>;
  scale_min?: number;
  scale_max?: number;
  placeholder?: string;
  required?: boolean;
}

/** Resolve the question text across the field names the model may use. */
function questionText(q: QuestionnaireQuestion): string {
  return q.prompt ?? q.question ?? q.label ?? q.text ?? q.title ?? "";
}

/** Normalise a kind string the model may emit (e.g. "single", "multiple"). */
function normKind(raw: unknown): QuestionnaireQuestion["kind"] {
  const k = String(raw ?? "").toLowerCase();
  if (k.includes("multi")) return "multi_choice";
  if (k.includes("single") || k === "choice" || k === "radio") return "single_choice";
  if (k.includes("scale") || k.includes("rating")) return "scale";
  return "open";
}

interface NormOption {
  label: string;
  value: string;
}

function normOptions(
  options: QuestionnaireQuestion["options"],
): NormOption[] {
  if (!Array.isArray(options)) return [];
  return options.map((o) => {
    if (o && typeof o === "object") {
      const value = String(o.value ?? o.label ?? "");
      const label = String(o.label ?? o.value ?? "");
      return { label, value };
    }
    return { label: String(o), value: String(o) };
  });
}

export interface QuestionnaireCardProps {
  title: string;
  intro?: string;
  questions: QuestionnaireQuestion[];
  submitLabel?: string;
  pending: boolean;
  onSubmit: (answers: Record<string, unknown>) => void | Promise<void>;
  onCancel: () => void;
}

export function QuestionnaireCard({
  title,
  intro,
  questions,
  submitLabel = "Enviar respuestas",
  pending,
  onSubmit,
  onCancel,
}: QuestionnaireCardProps) {
  const [answers, setAnswers] = useState<Record<string, unknown>>({});

  function set(id: string, value: unknown) {
    setAnswers((prev) => ({ ...prev, [id]: value }));
  }

  function toggleMulti(id: string, opt: string) {
    setAnswers((prev) => {
      const current = (prev[id] as string[] | undefined) ?? [];
      const exists = current.includes(opt);
      return {
        ...prev,
        [id]: exists ? current.filter((x) => x !== opt) : [...current, opt],
      };
    });
  }

  function missingRequired(): boolean {
    return questions.some((q, i) => {
      if (!q.required) return false;
      const v = answers[q.id || `q${i}`];
      if (v === undefined || v === null || v === "") return true;
      if (Array.isArray(v) && v.length === 0) return true;
      return false;
    });
  }

  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface p-6 my-3 max-w-lg shadow-soft border border-ink/[0.06]">
        <div className="space-y-1 mb-5">
          <h4 className="font-medium text-base text-ink leading-tight">{title}</h4>
          {intro && <p className="text-xs text-stone">{intro}</p>}
        </div>
        <div className="space-y-5">
          {questions.map((q, qi) => {
            const qid = q.id || `q${qi}`;
            const kind = normKind(q.kind);
            const text = questionText(q);
            const opts = normOptions(q.options);
            // single/multi without options would render a blank row — fall back
            // to a free-text box so the question is still answerable.
            const effKind =
              (kind === "single_choice" || kind === "multi_choice") && opts.length === 0
                ? "open"
                : kind;
            return (
              <div key={qid} className="space-y-2">
                {text && (
                  <p className="text-sm font-medium text-ink">
                    {text}
                    {q.required && <span className="text-danger ml-0.5">*</span>}
                  </p>
                )}
                {effKind === "single_choice" && (
                  <div className="flex flex-wrap gap-2">
                    {opts.map((opt) => (
                      <ChipOption
                        key={opt.value}
                        checked={answers[qid] === opt.value}
                        onChange={() => set(qid, opt.value)}
                        name={qid}
                        type="radio"
                        label={opt.label}
                      />
                    ))}
                  </div>
                )}
                {effKind === "multi_choice" && (
                  <div className="flex flex-wrap gap-2">
                    {opts.map((opt) => {
                      const checked = ((answers[qid] as string[] | undefined) ?? []).includes(opt.value);
                      return (
                        <ChipOption
                          key={opt.value}
                          checked={checked}
                          onChange={() => toggleMulti(qid, opt.value)}
                          name={qid}
                          type="checkbox"
                          label={opt.label}
                        />
                      );
                    })}
                  </div>
                )}
                {effKind === "scale" && (
                  <ScaleInput
                    value={(answers[qid] as number | undefined) ?? 0}
                    min={q.scale_min ?? 1}
                    max={q.scale_max ?? 5}
                    onChange={(v) => set(qid, v)}
                  />
                )}
                {effKind === "open" && (
                  <Textarea
                    value={(answers[qid] as string | undefined) ?? ""}
                    onChange={(e) => set(qid, e.target.value)}
                    placeholder={q.placeholder}
                    rows={3}
                  />
                )}
              </div>
            );
          })}
        </div>
        <div className="flex gap-2 mt-6">
          <Button
            size="sm"
            disabled={missingRequired()}
            loading={pending}
            onClick={() => void onSubmit(answers)}
          >
            {pending ? "Enviando" : submitLabel}
          </Button>
          <Button size="sm" variant="ghost" onClick={onCancel}>
            Cancelar
          </Button>
        </div>
      </div>
    </ChatMessageMotion>
  );
}

function ChipOption({
  checked,
  onChange,
  name,
  type,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  name: string;
  type: "radio" | "checkbox";
  label: string;
}) {
  return (
    <label
      className={cn(
        "text-xs rounded-tag px-3 py-1.5 border cursor-pointer transition-colors duration-180 ease-pirsch",
        checked
          ? "bg-ink text-canvas border-ink"
          : "bg-canvas border-ink/15 hover:border-ink/30 hover:bg-ink/[0.02] text-ink",
      )}
    >
      <input
        type={type}
        className="sr-only"
        name={name}
        checked={checked}
        onChange={onChange}
      />
      {label}
    </label>
  );
}

function ScaleInput({
  value,
  min,
  max,
  onChange,
}: {
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  const steps = Array.from({ length: max - min + 1 }, (_, i) => min + i);
  return (
    <div className="flex items-center gap-1.5">
      {steps.map((s) => (
        <button
          key={s}
          type="button"
          onClick={() => onChange(s)}
          className={cn(
            "h-9 w-9 rounded-full text-xs font-medium transition-all duration-180 ease-pirsch border",
            value === s
              ? "bg-leaf text-ink border-leaf scale-105"
              : "bg-canvas border-ink/15 hover:border-ink/30 text-stone hover:text-ink",
          )}
        >
          {s}
        </button>
      ))}
    </div>
  );
}
