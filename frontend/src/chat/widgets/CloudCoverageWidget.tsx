/**
 * CloudCoverageWidget — matrix of cloud providers × services + IaC + cost.
 *
 * Data: {
 *   providers: string[],
 *   services_by_provider?: Record<string, string[]>,
 *   services?: string[],      // legacy flat list
 *   iac_tool?: string,
 *   observability_stack?: string[],
 *   cost_model?: string,
 *   platform_maturity?: number   // 1..5
 * }
 */
import { Badge } from "@/ui";

interface CloudCoverageData {
  providers?: string[];
  services_by_provider?: Record<string, string[]>;
  services?: string[];
  iac_tool?: string;
  observability_stack?: string[];
  cost_model?: string;
  platform_maturity?: number;
}

const PROVIDER_TONE: Record<string, string> = {
  AWS: "bg-amber-100 text-amber-800",
  aws: "bg-amber-100 text-amber-800",
  GCP: "bg-blue-100 text-blue-800",
  gcp: "bg-blue-100 text-blue-800",
  Azure: "bg-sky-100 text-sky-800",
  azure: "bg-sky-100 text-sky-800",
  DO: "bg-blue-100 text-blue-800",
  OnPrem: "bg-stone/15 text-ink",
};

export function CloudCoverageWidget({ data }: { data: CloudCoverageData }) {
  const providers = data.providers ?? [];
  const byProvider = data.services_by_provider ?? {};
  const legacyServices = data.services ?? [];
  if (!providers.length && !legacyServices.length) {
    return (
      <p className="text-sm text-stone">
        Sin postura cloud capturada. Habla con el agente sobre tus servicios
        AWS/GCP/Azure para llenarlo.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-1.5">
        {providers.map((p) => (
          <Badge key={p} tone="stone" className={PROVIDER_TONE[p]}>
            {p}
          </Badge>
        ))}
      </div>

      {providers.length > 0 && Object.keys(byProvider).length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {providers.map((p) => {
            const services = byProvider[p] ?? [];
            return (
              <div
                key={p}
                className="rounded-card bg-surface border border-hairline px-3 py-2"
              >
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <Badge tone="stone" className={PROVIDER_TONE[p]}>
                    {p}
                  </Badge>
                  <span className="text-[10px] text-stone tabular-nums">
                    {services.length} svc
                  </span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {services.length === 0 ? (
                    <span className="text-[11px] text-stone italic">
                      sin servicios capturados
                    </span>
                  ) : (
                    services.map((s, i) => (
                      <span
                        key={i}
                        className="text-[10px] bg-ink/[0.05] text-ink/85 px-1.5 py-0.5 rounded-full"
                      >
                        {s}
                      </span>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : legacyServices.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {legacyServices.map((s, i) => (
            <span
              key={i}
              className="text-[11px] bg-ink/[0.05] text-ink/85 px-2 py-1 rounded-full"
            >
              {s}
            </span>
          ))}
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-2 text-[11px]">
        {data.iac_tool ? <KV k="IaC" v={data.iac_tool} /> : null}
        {data.cost_model ? <KV k="Coste" v={data.cost_model} /> : null}
        {data.platform_maturity !== undefined ? (
          <KV k="Platform" v={`${data.platform_maturity}/5`} />
        ) : null}
        {data.observability_stack?.length ? (
          <KV k="Obs" v={data.observability_stack.join(", ")} />
        ) : null}
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
