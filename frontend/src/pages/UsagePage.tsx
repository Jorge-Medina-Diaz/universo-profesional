import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { Cpu, TrendingUp, PieChart, BarChart3 } from "lucide-react";
import { llmUsage } from "@/shared/api-extra";
import {
  Badge,
  Card,
  PageHeader,
  PageSkeleton,
  Reveal,
  Surface,
  cn,
} from "@/ui";
import { queryKeys } from "@/shared/queryKeys";

interface DailyRow {
  day: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_eur: number;
}

interface ModelBreakdown {
  model: string;
  cost_eur: number;
  tokens: number;
  runs: number;
}

interface AgentBreakdown {
  agent: string;
  cost_eur: number;
  tokens: number;
  runs: number;
}

interface UsageSummary {
  total_cost_eur: number;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  by_model: ModelBreakdown[];
  by_agent: AgentBreakdown[];
}

interface UsageResponse {
  period: { year: number; month: number };
  summary: UsageSummary;
  daily: DailyRow[];
  free_tier_tokens: number;
}

export function UsagePage() {
  const query = useQuery({
    queryKey: queryKeys.llm.usage,
    queryFn: () => llmUsage.summary(),
  });

  const data = query.data;

  return (
    <Surface width="lg" spacing="md">
      <PageHeader
        eyebrow="Observabilidad"
        title="Uso de IA"
        subtitle="Costes, tokens y actividad de agentes en tiempo real."
      />

      {query.isLoading ? (
        <PageSkeleton />
      ) : !data ? (
        <Card tone="glass" padding="lg" className="text-center space-y-3">
          <h3 className="text-heading-sm font-medium tracking-tight">
            Sin datos de uso
          </h3>
          <p className="text-sm text-stone max-w-md mx-auto">
            Cuando empieces a interactuar con los agentes, verás aquí el desglose
            de costes y tokens.
          </p>
        </Card>
      ) : (
        <div className="flex flex-col gap-6">
          <CostGauge data={data} />
          <TokenChart daily={data.daily} />
          <ModelBreakdownCard models={data.summary.by_model} />
          <AgentActivity agents={data.summary.by_agent} />
        </div>
      )}
    </Surface>
  );
}

function CostGauge({ data }: { data: UsageResponse }) {
  const pct = Math.min(
    100,
    (data.summary.total_tokens / data.free_tier_tokens) * 100,
  );
  const color = pct > 90 ? "bg-sunbeam" : pct > 60 ? "bg-sunbeam-soft" : "bg-leaf";

  return (
    <Reveal>
      <Card padding="lg" tone="glass">
        <div className="flex items-center gap-3 mb-4">
          <TrendingUp size={18} className="text-stone" />
          <h2 className="text-heading-sm font-medium tracking-tight">
            Coste mensual
          </h2>
          <Badge tone="stone" size="sm" className="ml-auto">
            {data.period.month}/{data.period.year}
          </Badge>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          <div className="space-y-1">
            <p className="text-[40px] font-medium leading-none tracking-tight">
              {data.summary.total_cost_eur.toFixed(6)}
            </p>
            <p className="text-sm text-stone">EUR</p>
          </div>
          <div className="space-y-1">
            <p className="text-[40px] font-medium leading-none tracking-tight">
              {data.summary.total_tokens.toLocaleString()}
            </p>
            <p className="text-sm text-stone">tokens</p>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-stone">
              <span>Uso vs límite free</span>
              <span>{pct.toFixed(0)}%</span>
            </div>
            <div className="h-2 rounded-full bg-surface overflow-hidden">
              <motion.div
                className={cn("h-full rounded-full", color)}
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.8, ease: "easeOut" }}
              />
            </div>
            <p className="text-[11px] text-stone">
              {data.free_tier_tokens.toLocaleString()} tokens/mes en plan Free
            </p>
          </div>
        </div>
      </Card>
    </Reveal>
  );
}

function TokenChart({ daily }: { daily: DailyRow[] }) {
  const maxTokens = useMemo(
    () => Math.max(1, ...daily.map((d) => d.total_tokens)),
    [daily],
  );

  if (daily.length === 0) {
    return (
      <Reveal delay={0.1}>
        <Card padding="lg" tone="surface">
          <div className="flex items-center gap-3 mb-4">
            <BarChart3 size={18} className="text-stone" />
            <h2 className="text-heading-sm font-medium tracking-tight">
              Tokens por día
            </h2>
          </div>
          <p className="text-sm text-stone text-center py-8">
            Sin actividad este mes
          </p>
        </Card>
      </Reveal>
    );
  }

  return (
    <Reveal delay={0.1}>
      <Card padding="lg" tone="surface">
        <div className="flex items-center gap-3 mb-4">
          <BarChart3 size={18} className="text-stone" />
          <h2 className="text-heading-sm font-medium tracking-tight">
            Tokens por día
          </h2>
        </div>
        <div className="flex items-end gap-1 h-40 overflow-x-auto">
          {daily.map((d) => {
            const inputH = (d.input_tokens / maxTokens) * 100;
            const outputH = (d.output_tokens / maxTokens) * 100;
            return (
              <div
                key={d.day}
                className="flex-1 min-w-[24px] flex flex-col justify-end gap-0.5 group relative"
              >
                <div className="flex gap-0.5 items-end h-full">
                  <div
                    className="w-full bg-leaf rounded-t-sm opacity-80 group-hover:opacity-100 transition-opacity"
                    style={{ height: `${inputH}%` }}
                  />
                  <div
                    className="w-full bg-sunbeam rounded-t-sm opacity-80 group-hover:opacity-100 transition-opacity"
                    style={{ height: `${outputH}%` }}
                  />
                </div>
                <span className="text-[9px] text-stone text-center truncate">
                  {d.day.slice(5)}
                </span>
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block bg-ink text-canvas text-[10px] px-2 py-1 rounded whitespace-nowrap z-10">
                  {d.day}: {d.input_tokens.toLocaleString()} in /{" "}
                  {d.output_tokens.toLocaleString()} out
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-4 mt-3 text-xs text-stone">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-leaf inline-block" />
            Input
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-sunbeam inline-block" />
            Output
          </span>
        </div>
      </Card>
    </Reveal>
  );
}

function ModelBreakdownCard({ models }: { models: ModelBreakdown[] }) {
  const totalCost = useMemo(
    () => models.reduce((s, m) => s + m.cost_eur, 0) || 1,
    [models],
  );

  if (models.length === 0) {
    return null;
  }

  return (
    <Reveal delay={0.15}>
      <Card padding="lg" tone="surface">
        <div className="flex items-center gap-3 mb-4">
          <PieChart size={18} className="text-stone" />
          <h2 className="text-heading-sm font-medium tracking-tight">
            Desglose por modelo
          </h2>
        </div>
        <div className="space-y-3">
          {models.map((m) => {
            const pct = (m.cost_eur / totalCost) * 100;
            return (
              <div key={m.model} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-ink">{m.model}</span>
                  <span className="text-stone tabular-nums">
                    {m.cost_eur.toFixed(6)} € · {m.tokens.toLocaleString()} tok
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-surface overflow-hidden">
                  <div
                    className="h-full bg-ink rounded-full"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </Reveal>
  );
}

function AgentActivity({ agents }: { agents: AgentBreakdown[] }) {
  if (agents.length === 0) {
    return null;
  }

  return (
    <Reveal delay={0.2}>
      <Card padding="lg" tone="surface">
        <div className="flex items-center gap-3 mb-4">
          <Cpu size={18} className="text-stone" />
          <h2 className="text-heading-sm font-medium tracking-tight">
            Actividad de agentes
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-stone border-b border-hairline">
                <th className="pb-2 font-medium">Agente</th>
                <th className="pb-2 font-medium text-right">Ejecuciones</th>
                <th className="pb-2 font-medium text-right">Tokens</th>
                <th className="pb-2 font-medium text-right">Coste (€)</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((a) => (
                <tr
                  key={a.agent}
                  className="border-b border-hairline/50 last:border-0"
                >
                  <td className="py-2.5 text-ink capitalize">{a.agent}</td>
                  <td className="py-2.5 text-right tabular-nums">{a.runs}</td>
                  <td className="py-2.5 text-right tabular-nums">
                    {a.tokens.toLocaleString()}
                  </td>
                  <td className="py-2.5 text-right tabular-nums">
                    {a.cost_eur.toFixed(6)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </Reveal>
  );
}
