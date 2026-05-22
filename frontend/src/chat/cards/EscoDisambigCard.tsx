/**
 * EscoDisambigCard — HITL card for ESCO quarantine resolution.
 *
 * Shown when the backend's ESCO entity linker returned SUGGESTED — i.e.
 * the personal entity couldn't be auto-linked with high enough confidence
 * but plausible candidates exist. The user picks one (or dismisses), and
 * the coordinator records the choice via `/api/v1/graph/quarantine/{id}/resolve`.
 */
import { useState } from "react";
import { Link2, X } from "lucide-react";
import { Badge, Button, ChatMessageMotion, cn } from "@/ui";

export interface EscoCandidate {
  uri: string;
  label: string; // "EscoSkill" | "Occupation"
  pref_label_es?: string | null;
  pref_label_en?: string | null;
  score: number; // 0..1
}

export interface EscoDisambigCardProps {
  entityKind: string;
  entityLabel: string;
  candidates: EscoCandidate[];
  pending: boolean;
  onPick: (chosenUri: string) => void | Promise<void>;
  onDismiss: () => void;
}

export function EscoDisambigCard({
  entityKind,
  entityLabel,
  candidates,
  pending,
  onPick,
  onDismiss,
}: EscoDisambigCardProps) {
  const [selected, setSelected] = useState<string | null>(
    candidates[0]?.uri ?? null,
  );

  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface my-3 max-w-lg shadow-soft border border-ink/[0.06] overflow-hidden">
        <header className="flex items-center gap-2 px-5 pt-5 pb-2">
          <Link2 className="w-4 h-4 text-stone" />
          <h3 className="text-base font-semibold flex-1">
            ¿A qué concepto se refiere?
          </h3>
          <Badge tone="stone">{entityKind}</Badge>
        </header>

        <p className="px-5 text-sm text-ink/70">
          Detecté <span className="font-medium text-ink">{entityLabel}</span>{" "}
          pero no estoy 100% seguro de a qué concepto canónico vincularlo.
          Elige la mejor coincidencia.
        </p>

        <ul className="px-3 py-4 space-y-2">
          {candidates.map((c) => {
            const label = c.pref_label_es ?? c.pref_label_en ?? c.uri;
            const isSelected = selected === c.uri;
            return (
              <li key={c.uri}>
                <button
                  type="button"
                  onClick={() => setSelected(c.uri)}
                  className={cn(
                    "w-full text-left rounded-input px-3 py-2 border transition-colors",
                    isSelected
                      ? "border-amber/60 bg-amber/5"
                      : "border-ink/[0.08] hover:border-ink/[0.15]",
                  )}
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-sm font-medium">{label}</span>
                    <span className="text-xs text-ink/50">
                      {(c.score * 100).toFixed(0)}%
                    </span>
                  </div>
                  {c.pref_label_en && c.pref_label_en !== label && (
                    <p className="text-xs text-ink/60 mt-1">
                      EN — {c.pref_label_en}
                    </p>
                  )}
                  <p className="text-[10px] text-ink/40 mt-1 font-mono break-all">
                    {c.uri}
                  </p>
                </button>
              </li>
            );
          })}
        </ul>

        <footer className="flex items-center gap-2 px-5 pb-5 pt-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={onDismiss}
            disabled={pending}
            className="gap-1.5"
          >
            <X className="w-3.5 h-3.5" />
            Ninguna encaja
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => selected && onPick(selected)}
            disabled={!selected || pending}
            className="ml-auto"
          >
            Vincular
          </Button>
        </footer>
      </div>
    </ChatMessageMotion>
  );
}
