import { useState, type KeyboardEvent } from "react";
import { X } from "lucide-react";
import { cn } from "./cn";

export interface ChipInputProps {
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  tone?: "leaf" | "sunbeam" | "stone" | "ink";
  id?: string;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
}

const TONES = {
  leaf: "bg-leaf-soft text-leaf-ink",
  sunbeam: "bg-sunbeam-soft text-sunbeam-ink",
  stone: "bg-field text-stone",
  ink: "bg-ink text-canvas",
};

/**
 * Free-form chip input. Type → Enter or comma to add. Backspace on empty
 * removes the last chip. Use for skill lists, perks, locations, etc.
 */
export function ChipInput({
  value,
  onChange,
  placeholder = "Añadir…",
  tone = "leaf",
  ...rest
}: ChipInputProps) {
  const [draft, setDraft] = useState("");

  const commit = (raw: string) => {
    const v = raw.trim();
    if (!v) return;
    if (value.includes(v)) return;
    onChange([...value, v]);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commit(draft);
      setDraft("");
    } else if (e.key === "Backspace" && draft === "" && value.length > 0) {
      e.preventDefault();
      onChange(value.slice(0, -1));
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-input bg-field px-3 py-2 min-h-[44px] border border-transparent focus-within:border-ink transition-colors duration-180 ease-pirsch">
      {value.map((v) => (
        <span
          key={v}
          className={cn(
            "inline-flex items-center gap-1 text-xs rounded-tag px-2.5 py-1",
            TONES[tone],
          )}
        >
          {v}
          <button
            type="button"
            aria-label={`Quitar ${v}`}
            onClick={() => onChange(value.filter((x) => x !== v))}
            className="opacity-60 hover:opacity-100 transition-opacity"
          >
            <X size={10} />
          </button>
        </span>
      ))}
      <input
        type="text"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKeyDown}
        onBlur={() => {
          if (draft) {
            commit(draft);
            setDraft("");
          }
        }}
        placeholder={value.length === 0 ? placeholder : ""}
        className="flex-1 min-w-[120px] bg-transparent outline-none text-sm placeholder:text-stone"
        {...rest}
      />
    </div>
  );
}
