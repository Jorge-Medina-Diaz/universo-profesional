/**
 * PortfolioRadarWidget — ranked portfolio items for a specific JD/role.
 *
 * Data: {
 *   job_title?: string,
 *   company?: string,
 *   ranked_items?: [{ name, type, score_0_100, signals_covered, rationale, url? }],
 *   missing_signals?: [{ heading, sector }],
 *   suggested_artifacts_to_add?: string[],
 * }
 */
import { Badge } from "@/ui";
import { Trophy, ArrowUpRight } from "lucide-react";

interface RankedItem {
  name?: string;
  type?: string;
  score_0_100?: number;
  signals_covered?: string[];
  rationale?: string;
  url?: string;
}

interface MissingSignal {
  heading?: string;
  sector?: string;
}

interface PortfolioRadarData {
  job_title?: string;
  company?: string;
  ranked_items?: RankedItem[];
  missing_signals?: MissingSignal[];
  suggested_artifacts_to_add?: string[];
}

export function PortfolioRadarWidget({ data }: { data: PortfolioRadarData }) {
  const items = data.ranked_items ?? [];
  if (!items.length) {
    return (
      <p className="text-sm text-stone">
        Aún sin items ranqueados para esta oferta. Pega el JD para que el
        agente compute el ranking.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <header className="flex items-center gap-2">
        <span
          aria-hidden
          className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-sunbeam-soft text-sunbeam-ink"
        >
          <Trophy size={14} />
        </span>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-ink">
            {data.job_title ?? "Oferta"}
          </div>
          {data.company ? (
            <div className="text-[11px] text-stone">{data.company}</div>
          ) : null}
        </div>
      </header>

      <ul className="flex flex-col gap-2">
        {items.slice(0, 8).map((it, i) => (
          <li
            key={i}
            className="rounded-card bg-surface border border-hairline px-3 py-2 flex flex-col gap-1.5"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-stone tabular-nums text-[10px] w-4">
                  {i + 1}
                </span>
                <span className="text-sm font-medium text-ink truncate">
                  {it.name ?? "—"}
                </span>
                {it.type ? (
                  <Badge tone="stone">{it.type}</Badge>
                ) : null}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <ScoreBar score={it.score_0_100 ?? 0} />
                {it.url ? (
                  <a
                    href={it.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-stone hover:text-ink"
                  >
                    <ArrowUpRight size={12} />
                  </a>
                ) : null}
              </div>
            </div>
            {it.rationale ? (
              <p className="text-[11px] text-ink/80 leading-snug">
                {it.rationale}
              </p>
            ) : null}
            {it.signals_covered?.length ? (
              <div className="flex flex-wrap gap-1">
                {it.signals_covered.slice(0, 5).map((s, j) => (
                  <span
                    key={j}
                    className="text-[10px] bg-leaf-soft text-leaf-ink px-1.5 py-0.5 rounded-full"
                  >
                    {s}
                  </span>
                ))}
              </div>
            ) : null}
          </li>
        ))}
      </ul>

      {data.missing_signals?.length ? (
        <div className="flex flex-col gap-1 border-t border-hairline pt-2">
          <span className="uppercase tracking-wide text-stone font-medium text-[10px]">
            Signals que la oferta pide y te faltan
          </span>
          <ul className="flex flex-col gap-0.5">
            {data.missing_signals.slice(0, 5).map((s, i) => (
              <li key={i} className="text-[11px] leading-snug">
                <span className="text-stone">[{s.sector ?? "?"}]</span>{" "}
                <span className="text-ink/85">{s.heading ?? "—"}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {data.suggested_artifacts_to_add?.length ? (
        <div className="flex flex-col gap-1">
          <span className="uppercase tracking-wide text-stone font-medium text-[10px]">
            Sugerencias para fortalecer
          </span>
          <ul className="flex flex-col gap-0.5">
            {data.suggested_artifacts_to_add.map((s, i) => (
              <li key={i} className="text-[11px] text-ink/85 leading-snug">
                · {s}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function ScoreBar({ score }: { score: number }) {
  const s = Math.max(0, Math.min(100, Math.round(score)));
  const tone =
    s >= 75 ? "bg-leaf-ink" : s >= 50 ? "bg-sunbeam-ink" : "bg-amber-500";
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 w-12 rounded-full bg-ink/[0.06] overflow-hidden">
        <div className={`h-full ${tone}`} style={{ width: `${s}%` }} />
      </div>
      <span className="text-[10px] text-stone tabular-nums w-7 text-right">
        {s}
      </span>
    </div>
  );
}
