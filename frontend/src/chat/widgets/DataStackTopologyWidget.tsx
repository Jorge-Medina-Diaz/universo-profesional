/**
 * DataStackTopologyWidget — SVG flow of sources → transforms → warehouse,
 * with streaming + governance badges.
 *
 * Data: {
 *   sources?: string[],
 *   transforms?: string[],
 *   warehouse?: string,
 *   orchestration?: string,
 *   streaming?: string,
 *   governance?: string[],
 * }
 */
import { Badge } from "@/ui";
import { ArrowRight } from "lucide-react";

interface DataStackData {
  sources?: string[];
  transforms?: string[];
  warehouse?: string;
  orchestration?: string;
  streaming?: string;
  governance?: string[];
}

export function DataStackTopologyWidget({ data }: { data: DataStackData }) {
  const sources = data.sources ?? [];
  const transforms = data.transforms ?? [];
  const warehouse = data.warehouse;
  const orchestration = data.orchestration;
  const streaming = data.streaming;
  const governance = data.governance ?? [];

  const empty =
    sources.length === 0 &&
    transforms.length === 0 &&
    !warehouse &&
    !orchestration;
  if (empty) {
    return (
      <p className="text-sm text-stone">
        Aún sin stack de datos. Habla con el agente sobre tu pipeline para que
        lo registre.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-[1fr_auto_1fr_auto_1fr] gap-2 items-center">
        <Column label="Sources" items={sources} tone="bg-stone/15 text-ink" />
        <ArrowRight size={14} className="text-stone shrink-0" />
        <Column
          label="Transform"
          items={transforms}
          tone="bg-sunbeam-soft text-sunbeam-ink"
        />
        <ArrowRight size={14} className="text-stone shrink-0" />
        <Column
          label="Sink"
          items={warehouse ? [warehouse] : []}
          tone="bg-leaf-soft text-leaf-ink"
        />
      </div>

      <div className="grid grid-cols-2 gap-2 text-[11px]">
        {orchestration ? <KV k="Orchestración" v={orchestration} /> : null}
        {streaming ? <KV k="Streaming" v={streaming} /> : null}
      </div>

      {governance.length > 0 ? (
        <div className="flex flex-col gap-1">
          <span className="uppercase tracking-wide text-stone font-medium text-[10px]">
            Governance
          </span>
          <div className="flex flex-wrap gap-1">
            {governance.map((g, i) => (
              <Badge key={i} tone="stone">
                {g}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Column({
  label,
  items,
  tone,
}: {
  label: string;
  items: string[];
  tone: string;
}) {
  return (
    <div className="flex flex-col gap-1 min-w-0">
      <span className="uppercase tracking-wide text-stone font-medium text-[10px]">
        {label}
      </span>
      <div className="flex flex-col gap-1">
        {items.length === 0 ? (
          <span className="text-[10px] text-stone italic">—</span>
        ) : (
          items.map((it, i) => (
            <span
              key={i}
              className={`text-[11px] px-2 py-1 rounded-card text-center truncate ${tone}`}
            >
              {it}
            </span>
          ))
        )}
      </div>
    </div>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="uppercase tracking-wide text-stone font-medium text-[10px]">
        {k}
      </span>
      <span className="text-ink/85">{v}</span>
    </div>
  );
}
