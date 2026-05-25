/**
 * Generic HITL card — the agent fills in a payload, the user confirms or rejects.
 */
import { type ReactNode } from "react";
import { Check, X } from "lucide-react";
import { Button, ChatMessageMotion, Badge, cn } from "@/ui";

export interface EntryCardProps {
  title: string;
  details: Record<string, unknown>;
  pending: boolean;
  onConfirm: () => void | Promise<void>;
  onReject: () => void;
  ctaLabel?: string;
  ctaDescription?: ReactNode;
  kind?: string;
}

const KIND_LABEL: Record<string, { label: string; tone: "leaf" | "sunbeam" | "stone" }> = {
  experience: { label: "Experiencia", tone: "leaf" },
  education: { label: "Educación", tone: "leaf" },
  project: { label: "Proyecto", tone: "sunbeam" },
  skill: { label: "Skill", tone: "sunbeam" },
  certification: { label: "Certificación", tone: "leaf" },
  course: { label: "Curso", tone: "leaf" },
  language: { label: "Idioma", tone: "stone" },
  achievement: { label: "Logro", tone: "sunbeam" },
  interest: { label: "Interés", tone: "stone" },
};

export function EntryCard({
  title,
  details,
  pending,
  onConfirm,
  onReject,
  ctaLabel = "Añadir",
  ctaDescription,
  kind,
}: EntryCardProps) {
  const visible = Object.entries(details).filter(
    ([, v]) =>
      v !== null && v !== undefined && v !== "" && !(Array.isArray(v) && v.length === 0),
  );
  const kindMeta = kind ? KIND_LABEL[kind] : undefined;
  return (
    <ChatMessageMotion>
      <div
        className={cn(
          "rounded-card bg-surface p-5 my-3 max-w-md border border-ink/[0.06] shadow-soft",
        )}
      >
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="min-w-0 space-y-1.5">
            {kindMeta && (
              <Badge tone={kindMeta.tone} size="sm">
                {kindMeta.label}
              </Badge>
            )}
            <h4 className="font-medium text-base text-ink leading-tight">{title}</h4>
          </div>
        </div>
        {ctaDescription && <p className="text-xs text-stone mb-3">{ctaDescription}</p>}
        <dl className="text-xs space-y-1.5 mb-4 border-t border-ink/5 pt-3">
          {visible.map(([k, v]) => (
            <DefRow key={k} k={k} v={v} />
          ))}
        </dl>
        <div className="flex gap-2">
          <Button
            size="sm"
            loading={pending}
            onClick={() => void onConfirm()}
            leadingIcon={!pending && <Check size={14} strokeWidth={2.5} />}
          >
            {pending ? "Guardando" : ctaLabel}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={onReject}
            leadingIcon={<X size={14} />}
          >
            Descartar
          </Button>
        </div>
      </div>
    </ChatMessageMotion>
  );
}

/**
 * Terminal state for an entity card once its tool call is `complete`.
 *
 * CopilotKit keeps rendering an action after the user responds, so without a
 * resolved view a confirmed card would otherwise sit on its interactive
 * buttons (or a stuck "Guardando" spinner if a follow-up run failed). We read
 * the tool-call `result` to show the right outcome.
 */
export function ResolvedEntryChip({
  kind,
  title,
  result,
}: {
  kind?: string;
  title: string;
  result?: string;
}) {
  const rejected = !!result && /rejected/i.test(result);
  const errored = !!result && /^error/i.test(result.trim());
  const kindMeta = kind ? KIND_LABEL[kind] : undefined;
  const tone = errored ? "stone" : rejected ? "stone" : "leaf";
  const Icon = errored || rejected ? X : Check;
  const label = errored ? "No se pudo guardar" : rejected ? "Descartado" : "Añadido";
  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface/60 px-4 py-3 my-3 max-w-md border border-ink/[0.05] flex items-center gap-2.5">
        <span
          className={cn(
            "grid place-items-center h-6 w-6 rounded-full shrink-0",
            tone === "leaf" ? "bg-leaf/15 text-leaf-ink" : "bg-ink/[0.06] text-stone",
          )}
        >
          <Icon size={13} strokeWidth={2.5} />
        </span>
        <div className="min-w-0">
          <span className="text-xs text-stone">{label}</span>
          {!errored && !rejected && (
            <span className="text-sm text-ink font-medium truncate"> · {title}</span>
          )}
        </div>
        {kindMeta && !errored && !rejected && (
          <Badge tone={kindMeta.tone} size="sm" className="ml-auto shrink-0">
            {kindMeta.label}
          </Badge>
        )}
      </div>
    </ChatMessageMotion>
  );
}

function DefRow({ k, v }: { k: string; v: unknown }) {
  let display: string;
  if (Array.isArray(v)) display = v.join(", ");
  else if (typeof v === "object" && v) display = JSON.stringify(v);
  else display = String(v);
  return (
    <div className="grid grid-cols-[110px_1fr] gap-3 items-baseline">
      <dt className="text-stone font-medium capitalize truncate" title={k}>
        {k.replace(/_/g, " ")}
      </dt>
      <dd className="text-ink break-words">{display}</dd>
    </div>
  );
}
