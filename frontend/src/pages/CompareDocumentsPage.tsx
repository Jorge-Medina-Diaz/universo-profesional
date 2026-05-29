/**
 * Side-by-side comparator for 2 generated documents.
 *
 * URL pattern: `#/compare?a=<doc_id>&b=<doc_id>` (or pick from the page).
 * Useful to A/B two CV templates against the same JD, or two attempts at
 * the same offer over time.
 */
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeftRight, FileDown, ChevronDown, MessageSquare } from "lucide-react";
import { documents, type DocumentDetail, type DocumentSummary } from "@/shared/api";
import { useChatState } from "@/chat/state";
import {
  Badge,
  Button,
  Card,
  PageHeader,
  PageSkeleton,
  Reveal,
  Surface,
  cn,
  toast,
} from "@/ui";
import { queryKeys } from "@/shared/queryKeys";
import { useJsonResume } from "@/shared/hooks/useJsonResume";

type DocSide = "a" | "b";

export function CompareDocumentsPage({ initialA, initialB }: { initialA?: string; initialB?: string }) {
  const list = useQuery({
    queryKey: queryKeys.documents.all,
    queryFn: () => documents.list(),
  });
  const [a, setA] = useState<string | undefined>(initialA);
  const [b, setB] = useState<string | undefined>(initialB);

  // If we land with no selection, pick the two most recent CVs.
  useEffect(() => {
    if (!list.data) return;
    if (a || b) return;
    const sorted = [...list.data].sort(
      (x, y) => new Date(y.created_at).getTime() - new Date(x.created_at).getTime(),
    );
    if (sorted[0]) setA(sorted[0].id);
    if (sorted[1]) setB(sorted[1].id);
  }, [list.data, a, b]);

  // Both detail queries must be declared before any conditional return.
  const queryA = useQuery({
    queryKey: queryKeys.documents.detail(a),
    queryFn: () => documents.get(a!),
    enabled: !!a,
  });
  const queryB = useQuery({
    queryKey: queryKeys.documents.detail(b),
    queryFn: () => documents.get(b!),
    enabled: !!b,
  });

  if (list.isLoading) return <PageSkeleton />;

  const docs = list.data ?? [];
  if (docs.length < 2) {
    return (
      <Surface width="md" spacing="md">
        <Card padding="lg" tone="glass" className="text-center space-y-3">
          <ArrowLeftRight size={28} className="mx-auto text-stone" />
          <h2 className="text-heading-sm font-medium tracking-tight">
            Necesitas al menos 2 documentos
          </h2>
          <p className="text-sm text-stone">
            Genera otro CV o carta para empezar a comparar.
          </p>
          <Button variant="cta" onClick={() => (window.location.hash = "#/cv/new")}>
            Generar otro
          </Button>
        </Card>
      </Surface>
    );
  }

  const askChat = () => {
    const docA = queryA.data;
    const docB = queryB.data;
    if (!docA || !docB) {
      toast.error("Selecciona dos documentos completos antes de pedir opinión");
      return;
    }
    useChatState.getState().setPendingInjection({
      content: buildOpinionPrompt(docA, docB),
    });
    window.location.hash = "#/";
  };

  return (
    <Surface width="xl" spacing="md">
      <PageHeader
        eyebrow="Comparar"
        title="Documentos lado a lado"
        subtitle="Útil para A/B testing entre plantillas o intentos sobre la misma oferta."
        actions={
          <Button
            variant="cta"
            onClick={askChat}
            disabled={!queryA.data || !queryB.data}
            leadingIcon={<MessageSquare size={14} />}
          >
            El chat opina
          </Button>
        }
      />

      <Reveal>
        <div className="grid md:grid-cols-2 gap-3 md:gap-6">
          <DocSelector
            side="a"
            value={a}
            onChange={setA}
            documents={docs}
            otherValue={b}
          />
          <DocSelector
            side="b"
            value={b}
            onChange={setB}
            documents={docs}
            otherValue={a}
          />
        </div>
      </Reveal>

      <div className="grid md:grid-cols-2 gap-3 md:gap-6">
        <DocPanel id={a} side="a" />
        <DocPanel id={b} side="b" />
      </div>
    </Surface>
  );
}

/** Build a chat prompt summarising both docs so the agent can recommend one.
 *  We send only the relevant fields (not full JSON) to keep the prompt tight
 *  but still useful for the agent to reason about. */
function buildOpinionPrompt(a: DocumentDetail, b: DocumentDetail): string {
  const summarise = (doc: DocumentDetail, label: string): string => {
    const r = (doc.content_json ?? {}) as Record<string, unknown>;
    const basics = (r.basics ?? {}) as Record<string, unknown>;
    const cover = (r as { cover_letter_body?: unknown }).cover_letter_body;
    const work = ((r.work ?? []) as Array<Record<string, unknown>>).slice(0, 4);
    const skills = ((r.skills ?? []) as Array<Record<string, unknown>>).slice(0, 12);
    const parts: string[] = [];
    parts.push(`### ${label} — ${doc.kind} · ${doc.template} · ${doc.language}`);
    if (typeof cover === "string" && cover.trim()) {
      parts.push(`Carta:\n${cover.slice(0, 1200)}`);
    } else {
      if (basics.summary) parts.push(`Resumen: ${String(basics.summary).slice(0, 600)}`);
      if (work.length) {
        parts.push(
          `Experiencia:\n${work
            .map(
              (w) =>
                `- ${w.position ?? w.role ?? "?"} @ ${w.name ?? w.company ?? "?"} (${w.startDate ?? ""}—${w.endDate ?? "actual"})`,
            )
            .join("\n")}`,
        );
      }
      if (skills.length) {
        parts.push(
          `Skills: ${skills.map((s) => String(s.name ?? "")).filter(Boolean).join(", ")}`,
        );
      }
    }
    return parts.join("\n\n");
  };

  return [
    "Compara estos dos documentos que he generado y dame tu opinión. ¿Cuál recomendarías y por qué? Sé concreto: estructura, tono, fit con la oferta si aplica, omisiones, riesgos. Si uno gana claramente, dilo. Si depende del contexto, propón un criterio de decisión.",
    summarise(a, "Documento A"),
    summarise(b, "Documento B"),
  ].join("\n\n");
}

function DocSelector({
  side,
  value,
  onChange,
  documents: docs,
  otherValue,
}: {
  side: DocSide;
  value: string | undefined;
  onChange: (id: string) => void;
  documents: DocumentSummary[];
  otherValue: string | undefined;
}) {
  return (
    <label className="flex items-center gap-3 rounded-card bg-surface px-4 py-3">
      <Badge tone={side === "a" ? "leaf" : "sunbeam"} size="sm">
        {side.toUpperCase()}
      </Badge>
      <div className="relative flex-1">
        <select
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          className="appearance-none w-full bg-transparent text-sm text-ink outline-none pr-8"
        >
          <option value="" disabled>
            Selecciona un documento…
          </option>
          {docs.map((d) => (
            <option key={d.id} value={d.id} disabled={d.id === otherValue}>
              {d.kind.toUpperCase()} · {d.template} · {d.language} ·{" "}
              {new Date(d.created_at).toLocaleDateString()}
            </option>
          ))}
        </select>
        <ChevronDown
          size={14}
          className="absolute right-0 top-1/2 -translate-y-1/2 text-stone pointer-events-none"
        />
      </div>
    </label>
  );
}

function DocPanel({ id, side }: { id: string | undefined; side: DocSide }) {
  const query = useQuery({
    queryKey: queryKeys.documents.detail(id),
    queryFn: () => documents.get(id!),
    enabled: !!id,
  });
  const { basics, work, skills, resume } = useJsonResume(query.data ?? null);
  const coverBody = resume?.cover_letter_body;

  if (!id) {
    return (
      <Card padding="lg" tone="canvas" bordered className="min-h-[200px] flex items-center justify-center">
        <p className="text-sm text-stone">Selecciona un documento</p>
      </Card>
    );
  }
  if (query.isLoading) {
    return (
      <Card padding="lg" tone="canvas" bordered>
        <div className="animate-pulse space-y-3">
          <div className="h-6 w-2/3 rounded bg-black/[0.04]" />
          <div className="h-4 w-1/2 rounded bg-black/[0.04]" />
          <div className="h-20 rounded bg-black/[0.04]" />
        </div>
      </Card>
    );
  }
  if (!query.data) return null;

  const doc = query.data;

  return (
    <Card padding="lg" tone="canvas" bordered className="space-y-4">
      <header
        className={cn(
          "flex items-start justify-between gap-3 pb-3 border-b border-ink/5",
        )}
      >
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge tone={side === "a" ? "leaf" : "sunbeam"} size="sm">
              {side.toUpperCase()}
            </Badge>
            <span className="text-sm font-medium text-ink truncate">
              {basics.name ?? doc.kind.toUpperCase()}
            </span>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            <Badge tone="stone" size="sm">
              {doc.template}
            </Badge>
            <Badge tone="stone" size="sm">
              {doc.language?.toUpperCase()}
            </Badge>
            <Badge tone="stone" size="sm">
              {new Date(doc.created_at).toLocaleDateString()}
            </Badge>
          </div>
        </div>
        {doc.has_pdf && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              window.open(`/api/v1/documents/${id}/pdf`, "_blank", "noopener,noreferrer")
            }
            leadingIcon={<FileDown size={12} />}
          >
            PDF
          </Button>
        )}
      </header>

      {coverBody && (
        <section>
          <h3 className="text-[11px] uppercase tracking-wider text-stone font-medium mb-1.5">
            Cuerpo de la carta
          </h3>
          <pre className="whitespace-pre-wrap text-sm leading-relaxed text-ink bg-surface p-3 rounded-card max-h-72 overflow-auto font-sans">
            {coverBody}
          </pre>
        </section>
      )}

      {!coverBody && basics.summary && (
        <section>
          <h3 className="text-[11px] uppercase tracking-wider text-stone font-medium mb-1.5">
            Resumen
          </h3>
          <p className="text-sm text-ink leading-relaxed">{basics.summary}</p>
        </section>
      )}

      {!coverBody && work.length > 0 && (
        <section>
          <h3 className="text-[11px] uppercase tracking-wider text-stone font-medium mb-2">
            Experiencia ({work.length})
          </h3>
          <ul className="space-y-2.5">
            {work.slice(0, 5).map((w, i) => (
              <li key={i} className="text-sm">
                <div className="font-medium text-ink leading-tight">
                  {w.position ?? w.role} — {w.name ?? w.company}
                </div>
                <div className="text-xs text-stone">
                  {w.startDate ?? ""} — {w.endDate ?? "Actual"}
                </div>
                {(w.highlights ?? []).length > 0 && (
                  <ul className="list-disc pl-4 mt-1 space-y-0.5 text-xs text-ink">
                    {(w.highlights ?? []).slice(0, 3).map((h: string, j: number) => (
                      <li key={j}>{h}</li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {!coverBody && skills.length > 0 && (
        <section>
          <h3 className="text-[11px] uppercase tracking-wider text-stone font-medium mb-2">
            Skills ({skills.length})
          </h3>
          <div className="flex flex-wrap gap-1">
            {skills.slice(0, 16).map((s, i) => (
              <span
                key={i}
                className="text-[11px] rounded-tag bg-surface text-ink px-2 py-0.5"
              >
                {s.name}
              </span>
            ))}
          </div>
        </section>
      )}
    </Card>
  );
}
