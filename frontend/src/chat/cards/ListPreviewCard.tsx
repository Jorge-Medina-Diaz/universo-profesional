/**
 * Display-only list rendered inside the chat. Used by the agent to surface
 * context the user already has (jobs, documents, reminders, integrations)
 * without forcing them to pick — each row is just an information unit with
 * an optional click-through that opens the corresponding page.
 *
 * If the agent wants the user to pick one, use `SelectFromListCard` instead.
 */
import {
  BellRing,
  Briefcase,
  FileText,
  Send,
  Coffee,
  Trophy,
  XCircle,
  Heart,
  ExternalLink,
  CalendarClock,
} from "lucide-react";
import { Badge, ChatMessageMotion, GitHubIcon, LinkedInIcon, cn } from "@/ui";

export type PreviewKind = "jobs" | "documents" | "reminders" | "integrations";

export interface PreviewItem {
  id: string;
  title?: string | null;
  subtitle?: string | null;
  [k: string]: unknown;
}

export interface ListPreviewCardProps {
  kind: PreviewKind;
  items: PreviewItem[];
  title?: string;
}

const JOB_STATUS = {
  interested: { label: "Interesado", tone: "stone" as const, Icon: Heart },
  applied: { label: "Aplicado", tone: "leaf" as const, Icon: Send },
  interviewing: { label: "Entrevistas", tone: "sunbeam" as const, Icon: Coffee },
  offer: { label: "Oferta", tone: "leaf" as const, Icon: Trophy },
  rejected: { label: "Rechazado", tone: "amber" as const, Icon: XCircle },
  archived: { label: "Archivado", tone: "stone" as const, Icon: Briefcase },
};

export function ListPreviewCard({ kind, items, title }: ListPreviewCardProps) {
  if (!items.length) {
    return (
      <ChatMessageMotion>
        <div className="rounded-card bg-surface p-4 my-3 max-w-md border border-ink/[0.06]">
          <p className="text-sm text-stone text-center">No hay nada que mostrar.</p>
        </div>
      </ChatMessageMotion>
    );
  }
  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface p-4 my-3 max-w-md border border-ink/[0.06] shadow-soft">
        {title && (
          <h4 className="text-sm font-medium text-ink mb-3 leading-tight">{title}</h4>
        )}
        <ul className="flex flex-col gap-1.5">
          {items.map((it) => (
            <li key={it.id}>
              <Row kind={kind} item={it} />
            </li>
          ))}
        </ul>
      </div>
    </ChatMessageMotion>
  );
}

function Row({ kind, item }: { kind: PreviewKind; item: PreviewItem }) {
  if (kind === "jobs") return <JobRow item={item} />;
  if (kind === "documents") return <DocumentRow item={item} />;
  if (kind === "reminders") return <ReminderRow item={item} />;
  return <IntegrationRow item={item} />;
}

function JobRow({ item }: { item: PreviewItem }) {
  const status = (item.status as keyof typeof JOB_STATUS) ?? "interested";
  const meta = JOB_STATUS[status] ?? JOB_STATUS.interested;
  const matchScore = typeof item.match_score === "number" ? (item.match_score as number) : null;
  return (
    <a
      href={`#/jobs`}
      className="flex items-start gap-3 rounded-card px-3 py-2.5 bg-canvas border border-ink/[0.06] hover:border-ink/15 transition-colors group"
    >
      <span
        aria-hidden
        className={cn(
          "inline-flex items-center justify-center w-7 h-7 rounded-full shrink-0 mt-0.5",
          meta.tone === "leaf" && "bg-leaf-soft text-leaf-ink",
          meta.tone === "sunbeam" && "bg-sunbeam-soft text-sunbeam-ink",
          meta.tone === "stone" && "bg-surface text-stone",
          meta.tone === "amber" && "bg-sunbeam-soft text-sunbeam-ink",
        )}
      >
        <meta.Icon size={12} />
      </span>
      <div className="min-w-0 flex-1 space-y-0.5">
        <div className="text-sm font-medium text-ink truncate leading-tight">
          {item.title ?? "Sin título"}
        </div>
        {(item.company_name as string | null) && (
          <div className="text-xs text-stone truncate">{item.company_name as string}</div>
        )}
        <div className="flex items-center gap-1.5 flex-wrap mt-1">
          <Badge tone={meta.tone} size="sm">
            {meta.label}
          </Badge>
          {matchScore != null && (
            <Badge tone="leaf" size="sm">
              {matchScore}% match
            </Badge>
          )}
        </div>
      </div>
      <ExternalLink
        size={12}
        className="text-stone group-hover:text-ink transition-colors mt-1 shrink-0"
      />
    </a>
  );
}

function DocumentRow({ item }: { item: PreviewItem }) {
  return (
    <a
      href={`#/documents/${item.id}`}
      className="flex items-start gap-3 rounded-card px-3 py-2.5 bg-canvas border border-ink/[0.06] hover:border-ink/15 transition-colors group"
    >
      <span className="inline-flex items-center justify-center w-7 h-7 rounded-full shrink-0 mt-0.5 bg-surface text-stone">
        <FileText size={12} />
      </span>
      <div className="min-w-0 flex-1 space-y-0.5">
        <div className="text-sm font-medium text-ink truncate leading-tight">
          {(item.kind as string) === "cover_letter" ? "Carta" : "CV"} · {item.template as string}
        </div>
        <div className="text-xs text-stone">
          {item.language as string} ·{" "}
          {item.created_at ? new Date(item.created_at as string).toLocaleDateString() : ""}
        </div>
      </div>
      <ExternalLink
        size={12}
        className="text-stone group-hover:text-ink transition-colors mt-1 shrink-0"
      />
    </a>
  );
}

function ReminderRow({ item }: { item: PreviewItem }) {
  const due = item.due_at ? new Date(item.due_at as string) : null;
  const overdue = due ? due.getTime() < Date.now() : false;
  return (
    <div className="flex items-start gap-3 rounded-card px-3 py-2.5 bg-canvas border border-ink/[0.06]">
      <span
        aria-hidden
        className={cn(
          "inline-flex items-center justify-center w-7 h-7 rounded-full shrink-0 mt-0.5",
          overdue ? "bg-sunbeam-soft text-sunbeam-ink" : "bg-surface text-stone",
        )}
      >
        <BellRing size={12} />
      </span>
      <div className="min-w-0 flex-1 space-y-0.5">
        <div className="text-sm font-medium text-ink leading-tight">
          {item.title as string}
        </div>
        {(item.body as string) && (
          <div className="text-xs text-stone line-clamp-2">{item.body as string}</div>
        )}
        {due && (
          <div className="flex items-center gap-1 text-[11px] text-stone mt-1">
            <CalendarClock size={10} />
            <span>{due.toLocaleDateString()}</span>
            {overdue && (
              <Badge tone="amber" size="sm">
                vencido
              </Badge>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function IntegrationRow({ item }: { item: PreviewItem }) {
  const provider = (item.provider as string) ?? "";
  const lastSync = item.last_synced_at ? new Date(item.last_synced_at as string) : null;
  const icon =
    provider === "github" ? (
      <GitHubIcon size={12} />
    ) : provider === "linkedin" ? (
      <LinkedInIcon size={12} />
    ) : (
      <ExternalLink size={12} />
    );
  return (
    <div className="flex items-start gap-3 rounded-card px-3 py-2.5 bg-canvas border border-ink/[0.06]">
      <span className="inline-flex items-center justify-center w-7 h-7 rounded-full shrink-0 mt-0.5 bg-surface text-stone">
        {icon}
      </span>
      <div className="min-w-0 flex-1 space-y-0.5">
        <div className="text-sm font-medium text-ink leading-tight capitalize">
          {provider}
        </div>
        {(item.username as string) && (
          <div className="text-xs text-stone truncate">{item.username as string}</div>
        )}
        <div className="flex items-center gap-1.5 flex-wrap mt-1">
          <Badge tone="leaf" size="sm" dot>
            conectado
          </Badge>
          {lastSync && (
            <span className="text-[11px] text-stone">
              sync: {lastSync.toLocaleDateString()}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
