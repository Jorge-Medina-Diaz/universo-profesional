/**
 * Generic A2UI selector — the agent presents N items and the user picks one.
 *
 * The agent supplies items as objects keyed by `id`; this component renders a
 * compact row per item with title + subtitle + optional metadata pills + a
 * radio. Tailored visual treatment per `kind` (jobs / documents / generic).
 *
 * Returns to the agent on confirm: { selected_id: string } — or { cancelled: true }.
 */
import { useMemo, useState } from "react";
import {
  Briefcase,
  Check,
  FileText,
  Filter,
  Send,
  Sparkles,
  Trophy,
  X,
  XCircle,
  Coffee,
  Heart,
} from "lucide-react";
import { Badge, Button, ChatMessageMotion, cn } from "@/ui";

export type SelectListKind = "jobs" | "documents" | "generic";

export interface SelectListItem {
  id: string;
  /** Primary text on each row */
  title?: string | null;
  /** Optional second line */
  subtitle?: string | null;
  /** Free-form metadata badges */
  badges?: { label: string; tone?: "leaf" | "sunbeam" | "stone" | "amber" | "danger" }[];
  /** Pass-through — used by some kinds (jobs status, etc.) */
  [k: string]: unknown;
}

export interface SelectFromListCardProps {
  kind: SelectListKind;
  items: SelectListItem[];
  /** Question text shown above the list */
  prompt?: string;
  /** Label on the confirm CTA */
  ctaLabel?: string;
  pending?: boolean;
  /** Show a filter input above the list when length > 5 */
  filterable?: boolean;
  onSelect: (id: string) => void | Promise<void>;
  onCancel: () => void;
}

const STATUS_META: Record<
  string,
  { label: string; tone: "leaf" | "sunbeam" | "stone" | "amber"; Icon: typeof Briefcase }
> = {
  interested: { label: "Interesado", tone: "stone", Icon: Heart },
  applied: { label: "Aplicado", tone: "leaf", Icon: Send },
  interviewing: { label: "Entrevistas", tone: "sunbeam", Icon: Coffee },
  offer: { label: "Oferta", tone: "leaf", Icon: Trophy },
  rejected: { label: "Rechazado", tone: "amber", Icon: XCircle },
  archived: { label: "Archivado", tone: "stone", Icon: Briefcase },
};

export function SelectFromListCard({
  kind,
  items,
  prompt,
  ctaLabel = "Continuar",
  pending = false,
  filterable,
  onSelect,
  onCancel,
}: SelectFromListCardProps) {
  const [selectedId, setSelectedId] = useState<string | null>(items[0]?.id ?? null);
  const [filter, setFilter] = useState("");
  const showFilter = (filterable ?? items.length > 5) && items.length > 1;

  const visible = useMemo(() => {
    if (!filter.trim()) return items;
    const q = filter.toLowerCase();
    return items.filter(
      (it) =>
        (it.title ?? "").toLowerCase().includes(q) ||
        (it.subtitle ?? "").toLowerCase().includes(q),
    );
  }, [items, filter]);

  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface p-5 my-3 max-w-md border border-ink/[0.06] shadow-soft">
        {prompt && (
          <p className="text-sm text-ink leading-snug mb-3 font-medium">{prompt}</p>
        )}
        {showFilter && (
          <label className="flex items-center gap-2 rounded-input bg-canvas px-2.5 py-1.5 mb-3 text-xs">
            <Filter size={12} className="text-stone shrink-0" />
            <input
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filtrar…"
              className="bg-transparent outline-none flex-1 text-ink placeholder:text-stone/70"
            />
          </label>
        )}
        <div className="flex flex-col gap-1.5 mb-4 max-h-72 overflow-y-auto -mx-1 px-1">
          {visible.map((it) => (
            <SelectRow
              key={it.id}
              kind={kind}
              item={it}
              selected={selectedId === it.id}
              onClick={() => setSelectedId(it.id)}
            />
          ))}
          {visible.length === 0 && (
            <p className="text-xs text-stone text-center py-4">Sin resultados</p>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            loading={pending}
            disabled={!selectedId}
            onClick={() => selectedId && void onSelect(selectedId)}
            leadingIcon={!pending && <Check size={14} strokeWidth={2.5} />}
          >
            {pending ? "Procesando" : ctaLabel}
          </Button>
          <Button size="sm" variant="ghost" onClick={onCancel} leadingIcon={<X size={14} />}>
            Cancelar
          </Button>
        </div>
      </div>
    </ChatMessageMotion>
  );
}

function SelectRow({
  kind,
  item,
  selected,
  onClick,
}: {
  kind: SelectListKind;
  item: SelectListItem;
  selected: boolean;
  onClick: () => void;
}) {
  const statusMeta =
    kind === "jobs" && typeof item.status === "string" ? STATUS_META[item.status as string] : null;
  const matchScore = kind === "jobs" && typeof item.match_score === "number" ? (item.match_score as number) : null;
  const docTemplate = kind === "documents" && typeof item.template === "string" ? (item.template as string) : null;
  const docLang = kind === "documents" && typeof item.language === "string" ? (item.language as string) : null;
  const docKind = kind === "documents" && typeof item.kind === "string" ? (item.kind as string) : null;
  const Icon = kind === "documents" ? FileText : kind === "jobs" ? statusMeta?.Icon ?? Briefcase : Sparkles;

  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        "group w-full flex items-start gap-3 rounded-card px-3 py-2.5 text-left transition-all duration-180 ease-pirsch",
        selected
          ? "bg-canvas border border-ink/15 shadow-soft"
          : "bg-canvas/40 border border-transparent hover:bg-canvas hover:border-ink/[0.08]",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "inline-flex items-center justify-center w-7 h-7 rounded-full shrink-0 mt-0.5 transition-colors",
          selected ? "bg-leaf-soft text-leaf-ink" : "bg-surface text-stone",
        )}
      >
        <Icon size={12} />
      </span>
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-center justify-between gap-2">
          <h4 className="text-sm font-medium text-ink truncate leading-tight">
            {item.title ?? "(sin título)"}
          </h4>
          <span
            aria-hidden
            className={cn(
              "inline-block w-4 h-4 rounded-full border-2 shrink-0 transition-colors",
              selected ? "border-leaf bg-leaf" : "border-ink/20 bg-transparent",
            )}
          />
        </div>
        {item.subtitle && (
          <p className="text-xs text-stone truncate">{item.subtitle}</p>
        )}
        <div className="flex items-center gap-1.5 flex-wrap">
          {statusMeta && (
            <Badge tone={statusMeta.tone} size="sm">
              {statusMeta.label}
            </Badge>
          )}
          {matchScore != null && (
            <Badge tone="leaf" size="sm">
              {matchScore}% match
            </Badge>
          )}
          {docKind && (
            <Badge tone="stone" size="sm">
              {docKind === "cover_letter" ? "Carta" : docKind.toUpperCase()}
            </Badge>
          )}
          {docTemplate && (
            <Badge tone="stone" size="sm">
              {docTemplate}
            </Badge>
          )}
          {docLang && (
            <Badge tone="stone" size="sm">
              {docLang.toUpperCase()}
            </Badge>
          )}
          {item.badges?.map((b, i) => (
            <Badge key={i} tone={b.tone ?? "stone"} size="sm">
              {b.label}
            </Badge>
          ))}
        </div>
      </div>
    </button>
  );
}
