/**
 * ArchitecturePatternsWidget — list of detected/captured architectural patterns.
 *
 * Data: {
 *   patterns: [{ name, status?, context?, tags?, related_project?,
 *                project_link?, consequences? }],
 *   adr_count?: number,
 * }
 */
import { Badge } from "@/ui";
import { Layers } from "lucide-react";

interface Pattern {
  name?: string;
  status?: string;
  context?: string;
  consequences?: string;
  tags?: string[];
  related_project?: string;
  project_link?: string;
}

interface ArchPatternsData {
  patterns?: Pattern[];
  adr_count?: number;
}

const STATUS_TONE: Record<string, string> = {
  proposed: "bg-stone/15 text-ink",
  accepted: "bg-leaf-soft text-leaf-ink",
  superseded: "bg-amber-100 text-amber-800",
  rejected: "bg-rose-100 text-rose-800",
};

export function ArchitecturePatternsWidget({
  data,
}: {
  data: ArchPatternsData;
}) {
  const patterns = data.patterns ?? [];
  if (!patterns.length) {
    return (
      <p className="text-sm text-stone">
        Sin patrones capturados. Habla con el agente sobre una decisión
        arquitectónica concreta (microservicios, event-driven, …) para empezar.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {data.adr_count !== undefined ? (
        <div className="flex items-center gap-2 text-[11px] text-stone">
          <Layers size={12} /> {data.adr_count} ADRs capturados
        </div>
      ) : null}
      <ul className="flex flex-col gap-2">
        {patterns.map((p, i) => {
          const tone = p.status ? STATUS_TONE[p.status] : null;
          return (
            <li
              key={i}
              className="rounded-card bg-surface border border-hairline px-3 py-2 flex flex-col gap-1.5"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="text-sm font-medium text-ink leading-snug">
                  {p.name ?? "Patrón"}
                </div>
                {p.status ? (
                  <Badge tone="stone" className={tone ?? undefined}>
                    {p.status}
                  </Badge>
                ) : null}
              </div>
              {p.context ? (
                <p className="text-[11px] text-ink/80 leading-snug line-clamp-2">
                  <span className="text-stone uppercase tracking-wide text-[9px]">
                    Context:
                  </span>{" "}
                  {p.context}
                </p>
              ) : null}
              {p.consequences ? (
                <p className="text-[11px] text-ink/80 leading-snug line-clamp-2">
                  <span className="text-stone uppercase tracking-wide text-[9px]">
                    Consequences:
                  </span>{" "}
                  {p.consequences}
                </p>
              ) : null}
              {p.tags?.length ? (
                <div className="flex flex-wrap gap-1">
                  {p.tags.map((t, j) => (
                    <span
                      key={j}
                      className="text-[10px] bg-ink/[0.05] text-stone px-1.5 py-0.5 rounded-full"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              ) : null}
              {p.project_link ? (
                <a
                  href={p.project_link}
                  className="text-[11px] text-ink underline-offset-2 hover:underline"
                >
                  ver proyecto →
                </a>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
