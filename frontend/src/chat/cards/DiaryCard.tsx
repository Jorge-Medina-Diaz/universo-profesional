/**
 * DiaryCard — the weekly career-diary check-in (backend `present_diary_card`).
 *
 * The agent opens a low-friction "Tu semana" card: optional focus-hint chips
 * (toggle to include) + one free-text line. Submit responds with
 * `JSON.stringify({chips, text})`; the subtle escape hatch responds with the
 * literal string 'nothing_new' — matching the backend tool contract.
 *
 * Streaming-hardened like FormCard: `focus_hints` can keep arriving while the
 * args stream (selection is keyed by chip VALUE, so late chips never shift
 * state), submit/`nothing_new` wait for `respondReady`, and the card disables
 * itself after responding or once the tool call completes.
 */
import { useState } from "react";
import { Button, Textarea, ChatMessageMotion, cn } from "@/ui";

export interface DiaryCardProps {
  /** Period label from the agent, e.g. "3–9 jun". */
  period: string;
  /** Optional focus hints — rendered as toggleable chips. */
  focusHints: string[];
  /** True once the tool call resolved (status === "complete") — render-only. */
  done?: boolean;
  /** False while the tool args are still streaming (`respond` not wired yet). */
  respondReady?: boolean;
  onSubmit: (payload: { chips: string[]; text: string }) => void;
  onNothingNew: () => void;
}

export function DiaryCard({
  period,
  focusHints,
  done = false,
  respondReady = true,
  onSubmit,
  onNothingNew,
}: DiaryCardProps) {
  const [selected, setSelected] = useState<string[]>([]);
  const [text, setText] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const disabled = done || submitted;
  // Hints stream in progressively — dedupe + drop empties on every render.
  const hints = Array.from(new Set(focusHints.map((h) => h.trim()).filter(Boolean)));
  const empty = selected.length === 0 && !text.trim();

  function toggle(hint: string) {
    setSelected((prev) =>
      prev.includes(hint) ? prev.filter((h) => h !== hint) : [...prev, hint],
    );
  }

  return (
    <ChatMessageMotion>
      <div
        className={cn(
          "rounded-card bg-surface p-6 my-3 max-w-lg shadow-soft border border-ink/[0.06]",
          disabled && "opacity-80",
        )}
      >
        <div className="space-y-1 mb-5">
          <h4 className="font-medium text-base text-ink leading-tight">Tu semana</h4>
          {period && <p className="text-xs text-stone">{period}</p>}
        </div>
        {hints.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {hints.map((hint) => {
              const checked = selected.includes(hint);
              return (
                <label
                  key={hint}
                  className={cn(
                    "text-xs rounded-tag px-3 py-1.5 border transition-colors duration-180 ease-pirsch",
                    disabled ? "cursor-not-allowed opacity-70" : "cursor-pointer",
                    checked
                      ? "bg-ink text-canvas border-ink"
                      : "bg-canvas border-ink/15 hover:border-ink/30 hover:bg-ink/[0.02] text-ink",
                  )}
                >
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={checked}
                    onChange={() => toggle(hint)}
                    disabled={disabled}
                  />
                  {hint}
                </label>
              );
            })}
          </div>
        )}
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="¿Qué has hecho? Una frase vale"
          rows={3}
          disabled={disabled}
        />
        <div className="flex items-center gap-2 mt-5">
          <Button
            size="sm"
            disabled={disabled || !respondReady || empty}
            onClick={() => {
              setSubmitted(true);
              onSubmit({ chips: selected, text: text.trim() });
            }}
          >
            {disabled ? "Apuntado" : respondReady ? "Apuntarlo" : "Preparando…"}
          </Button>
          <button
            type="button"
            disabled={disabled || !respondReady}
            onClick={() => {
              setSubmitted(true);
              onNothingNew();
            }}
            className="text-xs text-stone hover:text-ink px-2 py-1.5 rounded-btn transition-colors duration-180 disabled:opacity-50 disabled:pointer-events-none"
          >
            Nada nuevo esta semana
          </button>
        </div>
      </div>
    </ChatMessageMotion>
  );
}
