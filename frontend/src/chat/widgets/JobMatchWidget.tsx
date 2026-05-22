/**
 * JobMatchWidget — display-only summary of a job match.
 *
 * Data: { match_score (0..100), job_title, company, strengths[], gaps[],
 *         suggested_keywords[], signals_gaps?: [{heading, sector}] }
 */
import { Badge } from "@/ui";

interface MatchData {
  match_score?: number;
  job_title?: string;
  company?: string;
  strengths?: string[];
  gaps?: string[];
  suggested_keywords?: string[];
  signals_gaps?: { heading?: string; sector?: string }[];
}

export function JobMatchWidget({ data }: { data: MatchData }) {
  const score = Math.round(data.match_score ?? 0);
  const tone =
    score >= 75 ? "leaf" : score >= 50 ? "sunbeam" : ("amber" as const);
  return (
    <div className="flex flex-col gap-3">
      <header className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-medium text-ink truncate">
            {data.job_title ?? "Oferta"}
          </div>
          {data.company ? (
            <div className="text-[11px] text-stone truncate">{data.company}</div>
          ) : null}
        </div>
        <Badge tone={tone}>{score}/100</Badge>
      </header>

      {data.strengths?.length ? (
        <Block label="Fortalezas" items={data.strengths} tone="leaf" />
      ) : null}
      {data.gaps?.length ? (
        <Block label="Gaps" items={data.gaps} tone="amber" />
      ) : null}
      {data.signals_gaps?.length ? (
        <div className="flex flex-col gap-1">
          <div className="uppercase tracking-wide text-stone font-medium text-[10px]">
            Signals concretos faltantes
          </div>
          <ul className="flex flex-col gap-0.5">
            {data.signals_gaps.slice(0, 5).map((g, i) => (
              <li key={i} className="text-[11px] text-ink/85 leading-snug">
                <span className="text-stone">[{g.sector ?? "?"}]</span>{" "}
                {g.heading ?? "—"}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {data.suggested_keywords?.length ? (
        <div className="flex flex-wrap gap-1">
          {data.suggested_keywords.map((k, i) => (
            <Badge key={i} tone="stone">
              {k}
            </Badge>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function Block({
  label,
  items,
  tone,
}: {
  label: string;
  items: string[];
  tone: "leaf" | "amber";
}) {
  const dot = tone === "leaf" ? "bg-leaf-ink" : "bg-amber-500";
  return (
    <div className="flex flex-col gap-1">
      <div className="uppercase tracking-wide text-stone font-medium text-[10px]">
        {label}
      </div>
      <ul className="flex flex-col gap-0.5">
        {items.slice(0, 5).map((it, i) => (
          <li key={i} className="flex items-start gap-2 text-[12px] leading-snug">
            <span className={`inline-block w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${dot}`} />
            <span className="text-ink/85">{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
