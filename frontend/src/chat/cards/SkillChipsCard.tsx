/**
 * Batch HITL card for skills.
 *
 * The agent often proposes 3-6 related skills at once (e.g. "tech stack of
 * your new role"). This card lets the user accept/reject per chip plus tune
 * the level inline before committing — far less click-heavy than 6 separate
 * EntryCards.
 *
 * Returns to the agent: `{ accepted: SkillProposal[], rejected: string[] }`.
 */
import { useMemo, useState } from "react";
import { motion } from "motion/react";
import { Check, Sparkles, X } from "lucide-react";
import { Badge, Button, ChatMessageMotion, cn } from "@/ui";

export type SkillCategory = "hard" | "soft" | "tool" | "methodology";
export type SkillLevel = "basic" | "intermediate" | "high" | "expert";

const LEVELS: SkillLevel[] = ["basic", "intermediate", "high", "expert"];
const LEVEL_LABEL: Record<SkillLevel, string> = {
  basic: "Básico",
  intermediate: "Medio",
  high: "Alto",
  expert: "Experto",
};

export interface SkillProposal {
  name: string;
  category?: SkillCategory;
  level?: SkillLevel;
  years?: number;
}

export interface SkillChipsCardProps {
  title?: string;
  intro?: string;
  skills: SkillProposal[];
  pending: boolean;
  onSubmit: (payload: { accepted: SkillProposal[]; rejected: string[] }) => void | Promise<void>;
  onCancel: () => void;
}

interface ChipState {
  skill: SkillProposal;
  selected: boolean;
}

export function SkillChipsCard({
  title = "Skills detectadas",
  intro,
  skills,
  pending,
  onSubmit,
  onCancel,
}: SkillChipsCardProps) {
  const [chips, setChips] = useState<ChipState[]>(() =>
    skills.map((s) => ({
      skill: { ...s, level: s.level ?? "intermediate" },
      selected: true,
    })),
  );

  const selectedCount = useMemo(
    () => chips.filter((c) => c.selected).length,
    [chips],
  );

  const toggle = (i: number) =>
    setChips((arr) =>
      arr.map((c, j) => (i === j ? { ...c, selected: !c.selected } : c)),
    );

  const setLevel = (i: number, level: SkillLevel) =>
    setChips((arr) =>
      arr.map((c, j) =>
        i === j ? { ...c, skill: { ...c.skill, level } } : c,
      ),
    );

  const submit = () => {
    const accepted = chips.filter((c) => c.selected).map((c) => c.skill);
    const rejected = chips.filter((c) => !c.selected).map((c) => c.skill.name);
    void onSubmit({ accepted, rejected });
  };

  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface p-5 my-3 max-w-lg shadow-soft border border-ink/[0.06]">
        <div className="flex items-start gap-3 mb-4">
          <span
            aria-hidden
            className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-canvas text-ink shrink-0"
          >
            <Sparkles size={18} />
          </span>
          <div className="min-w-0 space-y-1">
            <Badge tone="sunbeam" size="sm">
              Skills · lote
            </Badge>
            <h4 className="font-medium text-base text-ink leading-tight">{title}</h4>
            {intro && <p className="text-xs text-stone">{intro}</p>}
          </div>
        </div>

        <ul className="flex flex-col gap-2 mb-4">
          {chips.map((c, i) => (
            <SkillRow
              key={`${c.skill.name}-${i}`}
              chip={c}
              onToggle={() => toggle(i)}
              onLevel={(lvl) => setLevel(i, lvl)}
            />
          ))}
        </ul>

        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-stone">
            {selectedCount === 0
              ? "Ninguna seleccionada"
              : `${selectedCount} de ${chips.length} seleccionadas`}
          </span>
          <div className="flex gap-2">
            <Button
              size="sm"
              loading={pending}
              disabled={selectedCount === 0 && !pending}
              onClick={submit}
              leadingIcon={!pending && <Check size={14} strokeWidth={2.5} />}
            >
              {pending
                ? "Guardando"
                : `Añadir ${selectedCount || ""}`.trim()}
            </Button>
            <Button size="sm" variant="ghost" onClick={onCancel}>
              Cancelar
            </Button>
          </div>
        </div>
      </div>
    </ChatMessageMotion>
  );
}

function SkillRow({
  chip,
  onToggle,
  onLevel,
}: {
  chip: ChipState;
  onToggle: () => void;
  onLevel: (lvl: SkillLevel) => void;
}) {
  return (
    <motion.li
      layout
      transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
      className={cn(
        "flex items-center gap-3 rounded-card p-3 border transition-colors duration-180 ease-pirsch",
        chip.selected
          ? "bg-canvas border-ink/8"
          : "bg-canvas/40 border-dashed border-ink/15 opacity-60",
      )}
    >
      <button
        type="button"
        onClick={onToggle}
        aria-pressed={chip.selected}
        aria-label={chip.selected ? `Quitar ${chip.skill.name}` : `Añadir ${chip.skill.name}`}
        className={cn(
          "shrink-0 w-7 h-7 rounded-full grid place-items-center transition-all duration-180 ease-pirsch",
          chip.selected
            ? "bg-leaf text-ink"
            : "border border-ink/15 text-stone hover:border-ink/40",
        )}
      >
        {chip.selected ? <Check size={14} strokeWidth={2.5} /> : <X size={12} />}
      </button>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-ink truncate">{chip.skill.name}</div>
        {chip.skill.category && (
          <div className="text-[11px] text-stone capitalize">{chip.skill.category}</div>
        )}
      </div>
      {chip.selected && (
        <div role="group" aria-label="Nivel" className="flex items-center gap-0.5 bg-surface rounded-tag p-0.5">
          {LEVELS.map((lvl) => {
            const active = chip.skill.level === lvl;
            return (
              <button
                key={lvl}
                type="button"
                onClick={() => onLevel(lvl)}
                aria-pressed={active}
                className={cn(
                  "text-[10px] px-2 py-1 rounded-full transition-colors duration-180 ease-pirsch font-medium",
                  active
                    ? "bg-canvas text-ink shadow-soft"
                    : "text-stone hover:text-ink",
                )}
              >
                {LEVEL_LABEL[lvl]}
              </button>
            );
          })}
        </div>
      )}
    </motion.li>
  );
}
