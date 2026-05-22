/**
 * Enhanced HITL card for time-bound entities (experience, education).
 *
 * Shows a horizontal scrubber visualising the date range, plus the structured
 * payload below. The agent uses the same proposal contract as EntryCard, so
 * actions.tsx can swap between the two by passing `variant: "timeline"`.
 */
import { Briefcase, GraduationCap, Check, X } from "lucide-react";
import { Badge, Button, ChatMessageMotion, cn } from "@/ui";

export interface TimelineCardProps {
  kind: "experience" | "education";
  title: string;
  organization?: string;
  start_date?: string | null;
  end_date?: string | null;
  is_current?: boolean;
  description?: string | null;
  details?: Record<string, unknown>;
  pending: boolean;
  onConfirm: () => void | Promise<void>;
  onReject: () => void;
  ctaLabel?: string;
}

export function TimelineCard({
  kind,
  title,
  organization,
  start_date,
  end_date,
  is_current,
  description,
  details,
  pending,
  onConfirm,
  onReject,
  ctaLabel = "Añadir",
}: TimelineCardProps) {
  const Icon = kind === "experience" ? Briefcase : GraduationCap;
  const kindLabel = kind === "experience" ? "Experiencia" : "Educación";
  const startLabel = formatDate(start_date);
  const endLabel = is_current ? "Actual" : formatDate(end_date);
  const duration = computeDuration(start_date, is_current ? null : end_date, is_current);
  const filtered = details
    ? Object.entries(details).filter(
        ([k, v]) =>
          ![
            "organization",
            "start_date",
            "end_date",
            "is_current",
            "description",
            "role",
            "degree",
            "institution",
          ].includes(k) &&
          v !== null &&
          v !== undefined &&
          v !== "" &&
          !(Array.isArray(v) && v.length === 0),
      )
    : [];

  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface p-5 my-3 max-w-md border border-ink/[0.06] shadow-soft">
        <div className="flex items-start gap-3 mb-4">
          <span
            aria-hidden
            className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-canvas text-ink shrink-0"
          >
            <Icon size={18} />
          </span>
          <div className="min-w-0 space-y-1">
            <Badge tone="leaf" size="sm">
              {kindLabel}
            </Badge>
            <h4 className="font-medium text-base text-ink leading-tight">{title}</h4>
            {organization && (
              <p className="text-sm text-stone leading-tight">{organization}</p>
            )}
          </div>
        </div>

        <Scrubber
          startLabel={startLabel}
          endLabel={endLabel}
          duration={duration}
          isCurrent={!!is_current}
        />

        {description && (
          <p className="text-sm text-ink leading-relaxed mt-4 line-clamp-3">
            {description}
          </p>
        )}

        {filtered.length > 0 && (
          <dl className="text-xs space-y-1.5 mt-3 pt-3 border-t border-ink/5">
            {filtered.map(([k, v]) => (
              <div key={k} className="grid grid-cols-[110px_1fr] gap-3 items-baseline">
                <dt className="text-stone font-medium capitalize truncate" title={k}>
                  {k.replace(/_/g, " ")}
                </dt>
                <dd className="text-ink break-words">{formatValue(v)}</dd>
              </div>
            ))}
          </dl>
        )}

        <div className="flex gap-2 mt-5">
          <Button
            size="sm"
            loading={pending}
            onClick={() => void onConfirm()}
            leadingIcon={!pending && <Check size={14} strokeWidth={2.5} />}
          >
            {pending ? "Guardando" : ctaLabel}
          </Button>
          <Button size="sm" variant="ghost" onClick={onReject} leadingIcon={<X size={14} />}>
            Descartar
          </Button>
        </div>
      </div>
    </ChatMessageMotion>
  );
}

function Scrubber({
  startLabel,
  endLabel,
  duration,
  isCurrent,
}: {
  startLabel: string;
  endLabel: string;
  duration: string | null;
  isCurrent: boolean;
}) {
  return (
    <div className="relative">
      <div className="relative h-1 rounded-full bg-canvas overflow-hidden">
        <div
          className={cn(
            "absolute inset-y-0 left-0 rounded-full",
            isCurrent
              ? "right-0 bg-gradient-to-r from-leaf via-leaf to-leaf/30"
              : "right-0 bg-leaf",
          )}
        />
      </div>
      <div className="flex items-center justify-between mt-3">
        <ScrubberNode label={startLabel} side="start" />
        {duration && (
          <Badge tone="stone" size="sm">
            {duration}
          </Badge>
        )}
        <ScrubberNode label={endLabel} side="end" pulse={isCurrent} />
      </div>
    </div>
  );
}

function ScrubberNode({
  label,
  side,
  pulse,
}: {
  label: string;
  side: "start" | "end";
  pulse?: boolean;
}) {
  return (
    <div className={cn("flex flex-col gap-1", side === "end" ? "items-end" : "items-start")}>
      <span
        aria-hidden
        className={cn(
          "inline-flex items-center justify-center w-3 h-3 rounded-full",
          pulse ? "bg-leaf animate-pulse" : "bg-leaf-ink",
        )}
      />
      <span className="text-[11px] text-stone whitespace-nowrap">{label}</span>
    </div>
  );
}

function formatDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

function computeDuration(
  start?: string | null,
  end?: string | null,
  isCurrent?: boolean,
): string | null {
  if (!start) return null;
  const startDate = new Date(start);
  if (Number.isNaN(startDate.getTime())) return null;
  const endDate = isCurrent
    ? new Date()
    : end
      ? new Date(end)
      : new Date();
  if (Number.isNaN(endDate.getTime())) return null;
  const months =
    (endDate.getFullYear() - startDate.getFullYear()) * 12 +
    (endDate.getMonth() - startDate.getMonth());
  if (months <= 0) return null;
  if (months < 12) return `${months} m`;
  const years = Math.floor(months / 12);
  const rem = months % 12;
  return rem ? `${years} a ${rem} m` : `${years} a`;
}

function formatValue(v: unknown): string {
  if (Array.isArray(v)) return v.join(", ");
  if (typeof v === "object" && v) return JSON.stringify(v);
  return String(v);
}
