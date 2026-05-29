/**
 * SignalCoverageWidget — rubric overlay visualization.
 *
 * Data: { sector?, signals: [{rubric_slug, sector, section_kind, heading,
 *         body_excerpt, status, confidence, evidence_count}],
 *         by_status: {own:N, practice:N, aspire:N, ...} }
 */
import { Badge } from "@/ui";

interface SignalRow {
  rubric_slug?: string;
  sector?: string;
  section_kind?: string;
  heading?: string;
  body_excerpt?: string;
  status?: string;
  confidence?: number;
  evidence_count?: number;
}

interface SignalCoverageData {
  sector?: string;
  signals?: SignalRow[];
  by_status?: Record<string, number>;
}

const STATUS_TONE: Record<string, { label: string; tone: string }> = {
  own: { label: "Dominas", tone: "bg-leaf-soft text-leaf-ink" },
  practice: { label: "Practicas", tone: "bg-sunbeam-soft text-sunbeam-ink" },
  aspire: { label: "Aspiras", tone: "bg-amber-100 text-amber-800" },
  teach: { label: "Enseñas", tone: "bg-purple-100 text-purple-800" },
  avoid: { label: "Evitar", tone: "bg-rose-100 text-rose-800" },
};

export function SignalCoverageWidget({ data }: { data: SignalCoverageData }) {
  const signals = data.signals ?? [];
  const byStatus = data.by_status ?? {};
  if (!signals.length) {
    return (
      <p className="text-sm text-stone">
        Aún no hay overlay calculado. Pídele al agente "recompute mis signals"
        para refrescar la cobertura del corpus de rúbricas.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-1.5">
        {Object.entries(byStatus).map(([k, v]) => {
          const tone = STATUS_TONE[k];
          return (
            <Badge key={k} tone="stone" className={tone?.tone}>
              {tone?.label ?? k}: {v}
            </Badge>
          );
        })}
      </div>
      <ul className="flex flex-col gap-2">
        {signals.slice(0, 20).map((s, i) => {
          const tone = s.status ? STATUS_TONE[s.status] : null;
          return (
            <li
              key={i}
              className="rounded-card bg-surface border border-hairline px-3 py-2 flex flex-col gap-1"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] text-stone tabular-nums">
                  {s.rubric_slug ?? "—"} · {s.section_kind ?? ""}
                </span>
                {tone ? (
                  <Badge tone="stone" className={tone.tone}>
                    {tone.label}
                  </Badge>
                ) : null}
              </div>
              {s.heading ? (
                <div className="text-sm font-medium text-ink leading-snug">
                  {s.heading}
                </div>
              ) : null}
              {s.body_excerpt ? (
                <p className="text-[11px] text-ink/80 leading-snug">
                  {s.body_excerpt}
                </p>
              ) : null}
              <div className="flex items-center gap-2 text-[10px] text-stone">
                <span className="tabular-nums">
                  conf {((s.confidence ?? 0) * 100).toFixed(0)}%
                </span>
                <span>·</span>
                <span>{s.evidence_count ?? 0} evidencias</span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
