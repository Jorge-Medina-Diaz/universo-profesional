/**
 * FormCard — the agent-piloted in-chat form (P2.D, backend `present_form`).
 *
 * The agent declares `{form_id, title, intro?, fields, submit_label?}` and the
 * user fills/adjusts the pre-seeded values right in the thread instead of
 * being interrogated field-by-field or sent to a settings page.
 *
 * Field kinds: text | textarea | select | multiselect | date | number | toggle.
 * Submit responds with JSON `{field_id: value}`; Cancel responds 'cancelled'.
 * Mirrors QuestionnaireCard's structure/styling (chips, Inputs, buttons).
 */
import { useState } from "react";
import { Button, Input, Switch, Textarea, ChatMessageMotion, cn } from "@/ui";

export type FormFieldKind =
  | "text"
  | "textarea"
  | "select"
  | "multiselect"
  | "date"
  | "number"
  | "toggle";

export interface FormCardField {
  id: string;
  label: string;
  kind: FormFieldKind;
  options?: Array<string | { label?: string; value?: string }>;
  value?: unknown;
  placeholder?: string;
}

/** Normalise a kind string the model may emit. */
function normKind(raw: unknown): FormFieldKind {
  const k = String(raw ?? "").toLowerCase();
  if (k.includes("textarea") || k === "longtext") return "textarea";
  if (k.includes("multi")) return "multiselect";
  if (k.includes("select") || k === "choice" || k === "radio") return "select";
  if (k === "date") return "date";
  if (k === "number" || k === "numeric") return "number";
  if (k === "toggle" || k === "boolean" || k === "switch" || k === "checkbox") return "toggle";
  return "text";
}

interface NormOption {
  label: string;
  value: string;
}

function normOptions(options: FormCardField["options"]): NormOption[] {
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

/** Agent-provided seed `value`s for every field (streaming-safe: computed on
 *  each render, since fields can keep arriving after the card first mounts). */
function seedValues(fields: FormCardField[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  fields.forEach((f, i) => {
    const id = f.id || `f${i}`;
    if (f.value === undefined || f.value === null) return;
    out[id] = f.value;
  });
  return out;
}

export interface FormCardProps {
  formId: string;
  title: string;
  intro?: string;
  fields: FormCardField[];
  submitLabel?: string;
  /** True once the tool call resolved (status === "complete") — render-only. */
  done?: boolean;
  /** False while the tool args are still streaming (`respond` not wired yet) —
   *  inputs are editable but submit/cancel wait, so a click never dead-ends. */
  respondReady?: boolean;
  onSubmit: (values: Record<string, unknown>) => void;
  onCancel: () => void;
}

export function FormCard({
  formId,
  title,
  intro,
  fields,
  submitLabel = "Guardar",
  done = false,
  respondReady = true,
  onSubmit,
  onCancel,
}: FormCardProps) {
  // Only the USER's edits live in state; agent seeds are derived per render
  // (fields stream in progressively) and merged underneath on read + submit.
  const [edits, setEdits] = useState<Record<string, unknown>>({});
  const [submitted, setSubmitted] = useState(false);
  const disabled = done || submitted;
  const values: Record<string, unknown> = { ...seedValues(fields), ...edits };

  function set(id: string, value: unknown) {
    setEdits((prev) => ({ ...prev, [id]: value }));
  }

  function toggleMulti(id: string, opt: string) {
    setEdits((prev) => {
      const merged = { ...seedValues(fields), ...prev };
      const current = Array.isArray(merged[id]) ? (merged[id] as string[]) : [];
      const exists = current.includes(opt);
      return {
        ...prev,
        [id]: exists ? current.filter((x) => x !== opt) : [...current, opt],
      };
    });
  }

  return (
    <ChatMessageMotion>
      <div
        data-form-id={formId}
        className={cn(
          "rounded-card bg-surface p-6 my-3 max-w-lg shadow-soft border border-ink/[0.06]",
          disabled && "opacity-80",
        )}
      >
        <div className="space-y-1 mb-5">
          <h4 className="font-medium text-base text-ink leading-tight">{title}</h4>
          {intro && <p className="text-xs text-stone">{intro}</p>}
        </div>
        <div className="space-y-5">
          {fields.map((f, fi) => {
            const id = f.id || `f${fi}`;
            const kind = normKind(f.kind);
            const opts = normOptions(f.options);
            // select/multiselect without options can't render chips — fall
            // back to free text so the field is still answerable.
            const effKind =
              (kind === "select" || kind === "multiselect") && opts.length === 0
                ? "text"
                : kind;
            const v = values[id];
            return (
              <div key={id} className="space-y-2">
                {f.label && effKind !== "toggle" && (
                  <p className="text-sm font-medium text-ink">{f.label}</p>
                )}
                {effKind === "text" && (
                  <Input
                    value={typeof v === "string" || typeof v === "number" ? String(v) : ""}
                    onChange={(e) => set(id, e.target.value)}
                    placeholder={f.placeholder}
                    disabled={disabled}
                  />
                )}
                {effKind === "textarea" && (
                  <Textarea
                    value={typeof v === "string" ? v : ""}
                    onChange={(e) => set(id, e.target.value)}
                    placeholder={f.placeholder}
                    rows={3}
                    disabled={disabled}
                  />
                )}
                {effKind === "select" && (
                  <div className="flex flex-wrap gap-2">
                    {opts.map((opt) => (
                      <ChipOption
                        key={opt.value}
                        checked={v === opt.value}
                        onChange={() => set(id, opt.value)}
                        name={`${formId}-${id}`}
                        type="radio"
                        label={opt.label}
                        disabled={disabled}
                      />
                    ))}
                  </div>
                )}
                {effKind === "multiselect" && (
                  <div className="flex flex-wrap gap-2">
                    {opts.map((opt) => {
                      const checked =
                        Array.isArray(v) && (v as string[]).includes(opt.value);
                      return (
                        <ChipOption
                          key={opt.value}
                          checked={checked}
                          onChange={() => toggleMulti(id, opt.value)}
                          name={`${formId}-${id}`}
                          type="checkbox"
                          label={opt.label}
                          disabled={disabled}
                        />
                      );
                    })}
                  </div>
                )}
                {effKind === "date" && (
                  <Input
                    type="date"
                    value={typeof v === "string" ? v.slice(0, 10) : ""}
                    onChange={(e) => set(id, e.target.value)}
                    disabled={disabled}
                  />
                )}
                {effKind === "number" && (
                  <Input
                    type="number"
                    value={v === undefined || v === null ? "" : String(v)}
                    onChange={(e) =>
                      set(id, e.target.value === "" ? undefined : Number(e.target.value))
                    }
                    placeholder={f.placeholder}
                    disabled={disabled}
                  />
                )}
                {effKind === "toggle" && (
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-ink">{f.label}</p>
                    <Switch
                      checked={v === true || v === "true"}
                      onChange={(checked) => set(id, checked)}
                      disabled={disabled}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <div className="flex gap-2 mt-6">
          <Button
            size="sm"
            disabled={disabled || !respondReady}
            onClick={() => {
              setSubmitted(true);
              onSubmit(values);
            }}
          >
            {disabled ? "Enviado" : respondReady ? submitLabel : "Preparando…"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={disabled || !respondReady}
            onClick={() => {
              setSubmitted(true);
              onCancel();
            }}
          >
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
  disabled,
}: {
  checked: boolean;
  onChange: () => void;
  name: string;
  type: "radio" | "checkbox";
  label: string;
  disabled?: boolean;
}) {
  return (
    <label
      className={cn(
        "text-xs rounded-tag px-3 py-1.5 border transition-colors duration-180 ease-pirsch",
        disabled ? "cursor-not-allowed opacity-70" : "cursor-pointer",
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
        disabled={disabled}
      />
      {label}
    </label>
  );
}
