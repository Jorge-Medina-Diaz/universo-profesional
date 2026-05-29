/**
 * AgentPatternsWidget — agent systems captured by agent_system_specialist.
 *
 * Data shape from `present_widget(kind="agent_patterns", ...)`:
 *   {
 *     patterns: [{
 *       name: string,
 *       framework?: string,            // CrewAI | LangGraph | Agno | Autogen | LlamaIndex | other
 *       orchestration?: string,        // free text or canonical (react|plan-and-execute|hierarchical|swarm)
 *       memory?: string,               // stateless|short-term|vector|hybrid
 *       evaluation?: string | string[],// "judge LLM" / ["offline","HITL"]
 *       scale?: number,                // 1..5 maturity self-assessment
 *       outcome?: string,
 *       project_link?: string,         // project id or url
 *     }]
 *   }
 */
import { Badge } from "@/ui";

interface AgentPattern {
  name?: string;
  framework?: string;
  orchestration?: string;
  memory?: string;
  evaluation?: string | string[];
  scale?: number;
  outcome?: string;
  project_link?: string;
}

interface AgentPatternsData {
  patterns?: AgentPattern[];
}

const FRAMEWORK_TONE: Record<string, string> = {
  CrewAI: "bg-purple-100 text-purple-800",
  crewai: "bg-purple-100 text-purple-800",
  LangGraph: "bg-emerald-100 text-emerald-800",
  langgraph: "bg-emerald-100 text-emerald-800",
  Agno: "bg-amber-100 text-amber-800",
  agno: "bg-amber-100 text-amber-800",
  Autogen: "bg-blue-100 text-blue-800",
  autogen: "bg-blue-100 text-blue-800",
  LlamaIndex: "bg-sky-100 text-sky-800",
  llamaindex: "bg-sky-100 text-sky-800",
};

const MEMORY_LABEL: Record<string, string> = {
  stateless: "stateless",
  "short-term": "short-term",
  short_term: "short-term",
  vector: "vector store",
  hybrid: "hybrid",
};

export function AgentPatternsWidget({ data }: { data: AgentPatternsData }) {
  const patterns = data.patterns ?? [];
  if (!patterns.length) {
    return (
      <p className="text-sm text-stone">
        Aún no hay sistemas agénticos capturados. Cuéntale al agente sobre uno —
        un RAG, un CrewAI, un workflow con LangGraph — y aparecerá aquí.
      </p>
    );
  }
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {patterns.map((p, i) => (
        <PatternCard key={`${p.name ?? "pattern"}-${i}`} pattern={p} />
      ))}
    </div>
  );
}

function PatternCard({ pattern }: { pattern: AgentPattern }) {
  const framework = pattern.framework?.trim();
  const tone = framework ? FRAMEWORK_TONE[framework] ?? "bg-stone/15 text-ink" : null;
  const evaluation = Array.isArray(pattern.evaluation)
    ? pattern.evaluation.join(", ")
    : pattern.evaluation;
  const memory = pattern.memory ? MEMORY_LABEL[pattern.memory] ?? pattern.memory : null;
  return (
    <div className="rounded-card bg-surface border border-hairline px-3 py-2.5 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <div className="text-sm font-medium text-ink leading-snug">
          {pattern.name ?? "Sistema agéntico"}
        </div>
        {framework ? (
          <Badge tone="stone" className={tone ?? undefined}>
            {framework}
          </Badge>
        ) : null}
      </div>
      <div className="grid grid-cols-2 gap-1.5 text-[11px]">
        {pattern.orchestration ? (
          <KV k="Orquestación" v={pattern.orchestration} />
        ) : null}
        {memory ? <KV k="Memoria" v={memory} /> : null}
        {evaluation ? <KV k="Eval" v={evaluation} /> : null}
        {pattern.scale !== undefined ? (
          <KV k="Madurez" v={`${pattern.scale}/5`} />
        ) : null}
      </div>
      {pattern.outcome ? (
        <p className="text-[11px] text-stone leading-snug">{pattern.outcome}</p>
      ) : null}
      {pattern.project_link ? (
        <a
          href={
            pattern.project_link.startsWith("http")
              ? pattern.project_link
              : `#/projects/${pattern.project_link}`
          }
          className="text-[11px] text-ink underline-offset-2 hover:underline"
          target={pattern.project_link.startsWith("http") ? "_blank" : undefined}
          rel="noreferrer"
        >
          ver proyecto →
        </a>
      ) : null}
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
