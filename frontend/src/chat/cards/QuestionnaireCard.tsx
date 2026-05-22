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
  prompt: string;
  options?: string[];
  scale_min?: number;
  scale_max?: number;
  placeholder?: string;
  required?: boolean;
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
    return questions.some((q) => {
      if (!q.required) return false;
      const v = answers[q.id];
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
          {questions.map((q) => (
            <div key={q.id} className="space-y-2">
              <p className="text-sm font-medium text-ink">
                {q.prompt}
                {q.required && <span className="text-red-500 ml-0.5">*</span>}
              </p>
              {q.kind === "single_choice" && (
                <div className="flex flex-wrap gap-2">
                  {(q.options ?? []).map((opt) => (
                    <ChipOption
                      key={opt}
                      checked={answers[q.id] === opt}
                      onChange={() => set(q.id, opt)}
                      name={q.id}
                      type="radio"
                      label={opt}
                    />
                  ))}
                </div>
              )}
              {q.kind === "multi_choice" && (
                <div className="flex flex-wrap gap-2">
                  {(q.options ?? []).map((opt) => {
                    const checked = ((answers[q.id] as string[] | undefined) ?? []).includes(opt);
                    return (
                      <ChipOption
                        key={opt}
                        checked={checked}
                        onChange={() => toggleMulti(q.id, opt)}
                        name={q.id}
                        type="checkbox"
                        label={opt}
                      />
                    );
                  })}
                </div>
              )}
              {q.kind === "scale" && (
                <ScaleInput
                  value={(answers[q.id] as number | undefined) ?? 0}
                  min={q.scale_min ?? 1}
                  max={q.scale_max ?? 5}
                  onChange={(v) => set(q.id, v)}
                />
              )}
              {q.kind === "open" && (
                <Textarea
                  value={(answers[q.id] as string | undefined) ?? ""}
                  onChange={(e) => set(q.id, e.target.value)}
                  placeholder={q.placeholder}
                  rows={3}
                />
              )}
            </div>
          ))}
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
          : "bg-canvas border-ink/15 hover:border-ink/30 hover:bg-black/[0.02] text-ink",
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
