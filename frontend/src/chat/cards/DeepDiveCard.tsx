/**
 * DeepDiveCard — multi-section card to gently extract structured info about
 * a domain the user is exploring.
 *
 * Activated by the agent via `present_deep_dive(...)`. Each section is one
 * of: multi_chips, single_chips, chip_input, scale, open.
 *
 * Sections render as motion-animated accordions; the first section (or any
 * marked `defaultOpen`) starts expanded. Submit returns
 * `{ topic, sections: { [sectionId]: value } }` to the agent.
 */
import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown, Sparkles } from "lucide-react";
import {
  Badge,
  Button,
  ChatMessageMotion,
  ChipInput,
  Textarea,
  cn,
} from "@/ui";

export type DeepDiveSectionKind =
  | "multi_chips"
  | "single_chips"
  | "chip_input"
  | "scale"
  | "open";

export interface DeepDiveSection {
  id: string;
  title: string;
  kind: DeepDiveSectionKind;
  description?: string;
  options?: string[];
  scale_min?: number;
  scale_max?: number;
  placeholder?: string;
  defaultOpen?: boolean;
  /** Optional pre-fill the agent passes when it already extracted hints. */
  defaultValue?: unknown;
}

export interface DeepDiveCardProps {
  title: string;
  intro?: string;
  domain: string;
  sections: DeepDiveSection[];
  pending: boolean;
  onSubmit: (answers: Record<string, unknown>) => void | Promise<void>;
  onSkip: () => void;
}

export function DeepDiveCard({
  title,
  intro,
  domain,
  sections,
  pending,
  onSubmit,
  onSkip,
}: DeepDiveCardProps) {
  const initialOpen = useMemo<Set<string>>(() => {
    const set = new Set<string>();
    const explicit = sections.filter((s) => s.defaultOpen).map((s) => s.id);
    if (explicit.length > 0) explicit.forEach((id) => set.add(id));
    else if (sections[0]) set.add(sections[0].id);
    return set;
  }, [sections]);

  const initialValues = useMemo<Record<string, unknown>>(() => {
    const out: Record<string, unknown> = {};
    for (const s of sections) {
      if (s.defaultValue !== undefined) out[s.id] = s.defaultValue;
    }
    return out;
  }, [sections]);

  const [open, setOpen] = useState<Set<string>>(initialOpen);
  const [values, setValues] = useState<Record<string, unknown>>(initialValues);

  const toggle = (id: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const set = (id: string, v: unknown) =>
    setValues((prev) => ({ ...prev, [id]: v }));

  const toggleMulti = (id: string, opt: string) =>
    setValues((prev) => {
      const cur = (prev[id] as string[] | undefined) ?? [];
      const has = cur.includes(opt);
      return { ...prev, [id]: has ? cur.filter((x) => x !== opt) : [...cur, opt] };
    });

  const empty = (id: string) => isEmpty(values[id]);

  const anyFilled = sections.some((s) => !empty(s.id));

  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface my-3 max-w-lg shadow-soft border border-ink/[0.06] overflow-hidden">
        <header className="px-5 pt-5 pb-3">
          <div className="flex items-start justify-between gap-2 mb-2">
            <h4 className="font-medium text-base text-ink leading-tight">{title}</h4>
            <Badge tone="leaf" size="sm" icon={<Sparkles size={10} />}>
              {domain}
            </Badge>
          </div>
          {intro ? <p className="text-xs text-stone leading-relaxed">{intro}</p> : null}
        </header>

        <div className="border-t border-ink/[0.05] divide-y divide-ink/[0.05]">
          {sections.map((section) => {
            const isOpen = open.has(section.id);
            const summary = summarizeValue(values[section.id]);
            return (
              <section key={section.id} className="px-5">
                <button
                  type="button"
                  onClick={() => toggle(section.id)}
                  className="w-full flex items-center justify-between gap-3 py-3 text-left group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/20 focus-visible:ring-offset-1 rounded-btn -mx-2 px-2"
                  aria-expanded={isOpen}
                >
                  <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                    <span className="text-sm font-medium text-ink leading-tight">
                      {section.title}
                    </span>
                    {!isOpen && summary ? (
                      <span className="text-xs text-stone truncate">{summary}</span>
                    ) : null}
                    {!isOpen && !summary && section.description ? (
                      <span className="text-xs text-stone truncate">
                        {section.description}
                      </span>
                    ) : null}
                  </div>
                  <ChevronDown
                    size={16}
                    className={cn(
                      "text-stone transition-transform duration-180 shrink-0",
                      isOpen && "rotate-180",
                    )}
                  />
                </button>
                <AnimatePresence initial={false}>
                  {isOpen ? (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
                      className="overflow-hidden"
                    >
                      <div className="pb-4 pt-1 space-y-2">
                        {section.description ? (
                          <p className="text-xs text-stone leading-relaxed">
                            {section.description}
                          </p>
                        ) : null}
                        <SectionInput
                          section={section}
                          value={values[section.id]}
                          onChange={(v) => set(section.id, v)}
                          onToggleMulti={(opt) => toggleMulti(section.id, opt)}
                        />
                      </div>
                    </motion.div>
                  ) : null}
                </AnimatePresence>
              </section>
            );
          })}
        </div>

        <footer className="flex items-center gap-2 px-5 py-4 bg-canvas/40">
          <Button
            size="sm"
            disabled={!anyFilled}
            loading={pending}
            onClick={() => void onSubmit(values)}
          >
            {pending ? "Guardando" : "Guardar todo"}
          </Button>
          <Button size="sm" variant="ghost" onClick={onSkip}>
            Esto no, otra cosa
          </Button>
        </footer>
      </div>
    </ChatMessageMotion>
  );
}

interface SectionInputProps {
  section: DeepDiveSection;
  value: unknown;
  onChange: (v: unknown) => void;
  onToggleMulti: (opt: string) => void;
}

function SectionInput({ section, value, onChange, onToggleMulti }: SectionInputProps) {
  if (section.kind === "multi_chips" || section.kind === "single_chips") {
    const opts = section.options ?? [];
    if (section.kind === "single_chips") {
      const current = value as string | undefined;
      return (
        <div className="flex flex-wrap gap-2">
          {opts.map((opt) => (
            <ChipOption
              key={opt}
              checked={current === opt}
              onChange={() => onChange(opt)}
              label={opt}
            />
          ))}
        </div>
      );
    }
    const arr = (value as string[] | undefined) ?? [];
    return (
      <div className="flex flex-wrap gap-2">
        {opts.map((opt) => (
          <ChipOption
            key={opt}
            checked={arr.includes(opt)}
            onChange={() => onToggleMulti(opt)}
            label={opt}
          />
        ))}
      </div>
    );
  }
  if (section.kind === "chip_input") {
    return (
      <ChipInput
        value={(value as string[] | undefined) ?? []}
        onChange={(next) => onChange(next)}
        placeholder={section.placeholder ?? "Añadir y pulsar Enter…"}
        tone="leaf"
      />
    );
  }
  if (section.kind === "scale") {
    const min = section.scale_min ?? 1;
    const max = section.scale_max ?? 5;
    return (
      <ScaleInput value={(value as number | undefined) ?? 0} min={min} max={max} onChange={onChange} />
    );
  }
  // open
  return (
    <Textarea
      value={(value as string | undefined) ?? ""}
      onChange={(e) => onChange(e.target.value)}
      placeholder={section.placeholder ?? "Escribe lo que se te ocurra…"}
      rows={3}
    />
  );
}

function ChipOption({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onChange}
      className={cn(
        "text-xs rounded-tag px-3 py-1.5 border cursor-pointer transition-colors duration-180 ease-pirsch focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/20 focus-visible:ring-offset-1",
        checked
          ? "bg-ink text-canvas border-ink"
          : "bg-canvas border-ink/15 hover:border-ink/30 hover:bg-ink/[0.02] text-ink",
      )}
      aria-pressed={checked}
    >
      {label}
    </button>
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
            "h-9 w-9 rounded-full text-xs font-medium transition-all duration-180 ease-pirsch border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/20 focus-visible:ring-offset-1",
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

function isEmpty(v: unknown): boolean {
  if (v === undefined || v === null) return true;
  if (typeof v === "string") return v.trim() === "";
  if (Array.isArray(v)) return v.length === 0;
  if (typeof v === "number") return false;
  return false;
}

function summarizeValue(v: unknown): string | null {
  if (isEmpty(v)) return null;
  if (Array.isArray(v)) {
    const arr = v as string[];
    if (arr.length === 0) return null;
    if (arr.length <= 3) return arr.join(" · ");
    return `${arr.slice(0, 3).join(" · ")} · +${arr.length - 3}`;
  }
  if (typeof v === "string") {
    return v.length > 60 ? v.slice(0, 60) + "…" : v;
  }
  if (typeof v === "number") return String(v);
  return null;
}
