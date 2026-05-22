/**
 * SecurityPostureWidget — gauge + breakdown by area.
 *
 * Data: {
 *   score?: number,            // 0..100 computed
 *   areas?: string[],
 *   practices?: string[],
 *   certs?: string[],
 *   maturity?: number,         // 1..5
 * }
 */
import { Badge } from "@/ui";
import { Shield } from "lucide-react";

interface SecurityPostureData {
  score?: number;
  areas?: string[];
  practices?: string[];
  certs?: string[];
  maturity?: number;
}

export function SecurityPostureWidget({ data }: { data: SecurityPostureData }) {
  const areas = data.areas ?? [];
  const practices = data.practices ?? [];
  const certs = data.certs ?? [];
  const score = Math.round(data.score ?? estimate(data));
  const tone =
    score >= 75 ? "leaf" : score >= 50 ? "sunbeam" : ("amber" as const);

  const empty =
    areas.length === 0 && practices.length === 0 && certs.length === 0;
  if (empty) {
    return (
      <p className="text-sm text-stone">
        Aún sin postura de seguridad capturada. Cuéntale al agente qué áreas
        tocas (AppSec, CloudSec, identity, compliance…).
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <header className="flex items-center gap-3">
        <span
          aria-hidden
          className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-leaf-soft text-leaf-ink"
        >
          <Shield size={16} />
        </span>
        <div className="flex-1">
          <div className="text-xl font-medium text-ink leading-none">
            {score}<span className="text-stone text-sm">/100</span>
          </div>
          <div className="text-[11px] text-stone mt-0.5">
            Madurez {data.maturity ?? "?"}/5 · {areas.length} áreas
          </div>
        </div>
        <Badge tone={tone}>{score >= 75 ? "Senior" : score >= 50 ? "Mid" : "Junior"}</Badge>
      </header>

      {areas.length > 0 ? (
        <Block label="Áreas" items={areas} tone="leaf" />
      ) : null}
      {practices.length > 0 ? (
        <Block label="Prácticas" items={practices} tone="stone" />
      ) : null}
      {certs.length > 0 ? (
        <Block label="Certificaciones" items={certs} tone="sunbeam" />
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
  tone: "leaf" | "stone" | "sunbeam";
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="uppercase tracking-wide text-stone font-medium text-[10px]">
        {label}
      </span>
      <div className="flex flex-wrap gap-1">
        {items.map((it, i) => (
          <Badge key={i} tone={tone}>
            {it}
          </Badge>
        ))}
      </div>
    </div>
  );
}

function estimate(d: SecurityPostureData): number {
  // Fallback if backend didn't pre-compute: rough heuristic.
  const a = (d.areas?.length ?? 0) * 8;
  const p = (d.practices?.length ?? 0) * 6;
  const c = (d.certs?.length ?? 0) * 10;
  const m = (d.maturity ?? 0) * 8;
  return Math.min(100, a + p + c + m);
}
