import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import {
  Plus,
  Pencil,
  Trash2,
  Sparkles,
  GitMerge,
  FileText,
  Activity as ActivityIcon,
  Filter,
} from "lucide-react";
import { universe, type ActivityEvent } from "@/shared/api";
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

interface EventMeta {
  label: string;
  Icon: typeof Plus;
  tone: "leaf" | "sunbeam" | "stone" | "amber";
}

const TYPE_META: Record<string, EventMeta> = {
  EntryAdded: { label: "Añadido", Icon: Plus, tone: "leaf" },
  EntryUpdated: { label: "Actualizado", Icon: Pencil, tone: "sunbeam" },
  EntryMerged: { label: "Fusionado", Icon: GitMerge, tone: "leaf" },
  EntryDeleted: { label: "Borrado", Icon: Trash2, tone: "amber" },
  DocumentGenerated: { label: "Documento generado", Icon: FileText, tone: "leaf" },
  SuggestionAccepted: { label: "Sugerencia aceptada", Icon: Sparkles, tone: "leaf" },
  SuggestionRejected: { label: "Sugerencia rechazada", Icon: Sparkles, tone: "stone" },
};

const FILTERS: Array<{ id: "all" | "writes" | "documents" | "suggestions"; label: string; types: string[] | null }> = [
  { id: "all", label: "Todo", types: null },
  {
    id: "writes",
    label: "Cambios en universo",
    types: ["EntryAdded", "EntryUpdated", "EntryMerged", "EntryDeleted"],
  },
  { id: "documents", label: "Documentos", types: ["DocumentGenerated"] },
  {
    id: "suggestions",
    label: "Sugerencias",
    types: ["SuggestionAccepted", "SuggestionRejected"],
  },
];

export function ActivityPage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");
  const activeFilter = FILTERS.find((f) => f.id === filter) ?? FILTERS[0];

  const query = useQuery({
    queryKey: queryKeys.activity.list(filter),
    queryFn: () =>
      universe.activity({
        limit: 100,
        types: activeFilter.types ?? undefined,
      }),
  });

  const grouped = useMemo(() => groupByDay(query.data ?? []), [query.data]);

  return (
    <Surface width="md" spacing="md">
      <PageHeader
        eyebrow="Actividad"
        title="Tu historia con el universo"
        subtitle="Cada cambio que hace el agente, tus importaciones, tus CVs generados. Todo cronológico."
      />

      <Reveal>
        <Card padding="md" tone="surface">
          <div className="flex items-center gap-2 flex-wrap">
            <Filter size={14} className="text-stone shrink-0" />
            {FILTERS.map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => setFilter(f.id)}
                aria-pressed={filter === f.id}
                className={cn(
                  "text-xs rounded-tag px-3 py-1.5 transition-colors duration-180 ease-pirsch font-medium",
                  filter === f.id
                    ? "bg-ink text-canvas"
                    : "bg-canvas text-stone hover:text-ink",
                )}
              >
                {f.label}
              </button>
            ))}
            {query.data && (
              <Badge tone="stone" size="sm" className="ml-auto">
                {query.data.length} eventos
              </Badge>
            )}
          </div>
        </Card>
      </Reveal>

      {query.isLoading ? (
        <PageSkeleton />
      ) : grouped.length === 0 ? (
        <Card padding="lg" className="text-center space-y-3">
          <span
            aria-hidden
            className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-leaf-soft text-leaf-ink mx-auto"
          >
            <ActivityIcon size={20} />
          </span>
          <h3 className="text-heading-sm font-medium tracking-tight">Sin actividad todavía</h3>
          <p className="text-sm text-stone max-w-md mx-auto">
            Cuando empieces a usar el agente, importes datos o generes CVs, verás
            cada paso aquí. Tu rastro completo, propio y revisable.
          </p>
        </Card>
      ) : (
        <div className="flex flex-col gap-6">
          {grouped.map((g) => (
            <DayGroup key={g.day} day={g.day} events={g.events} />
          ))}
        </div>
      )}
    </Surface>
  );
}

function DayGroup({ day, events }: { day: string; events: ActivityEvent[] }) {
  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-wider text-stone font-medium mb-3 capitalize sticky top-16 bg-canvas/80 backdrop-blur-md py-1 z-10">
        {day}
      </h3>
      <ol className="relative space-y-0.5">
        <span
          aria-hidden
          className="absolute left-4 top-3 bottom-3 w-px bg-ink/8 -z-10"
        />
        {events.map((event, i) => (
          <EventRow key={event.event_id} event={event} index={i} />
        ))}
      </ol>
    </section>
  );
}

function EventRow({ event, index }: { event: ActivityEvent; index: number }) {
  const meta = TYPE_META[event.event_type] ?? {
    label: event.event_type,
    Icon: ActivityIcon,
    tone: "stone" as const,
  };
  const Icon = meta.Icon;
  const time = new Date(event.occurred_at).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
  const summary = describeEvent(event);
  return (
    <motion.li
      initial={{ opacity: 0, x: -4 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.24, delay: index * 0.02, ease: [0.2, 0.8, 0.2, 1] }}
      className="flex items-start gap-3"
    >
      <span
        aria-hidden
        className={cn(
          "shrink-0 w-8 h-8 rounded-full inline-flex items-center justify-center relative z-10 mt-1",
          meta.tone === "leaf" && "bg-leaf-soft text-leaf-ink",
          meta.tone === "sunbeam" && "bg-sunbeam-soft text-sunbeam-ink",
          meta.tone === "stone" && "bg-canvas border border-ink/10 text-stone",
          meta.tone === "amber" && "bg-sunbeam-soft text-sunbeam-ink",
        )}
      >
        <Icon size={14} />
      </span>
      <Card padding="sm" tone="surface" className="flex-1 min-w-0 mb-2">
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <Badge tone={meta.tone} size="sm">
            {meta.label}
          </Badge>
          <span className="ml-auto text-[11px] text-stone tabular-nums">{time}</span>
        </div>
        <p className="text-sm text-ink leading-snug">{summary}</p>
      </Card>
    </motion.li>
  );
}

function describeEvent(event: ActivityEvent): string {
  const p = event.payload ?? {};
  const entityType = (p.entity_type as string) ?? "";
  switch (event.event_type) {
    case "EntryAdded":
      return `Nueva entrada en ${entityType || "tu universo"}`;
    case "EntryUpdated":
      return `Actualizaste ${entityType || "una entrada"}`;
    case "EntryMerged":
      return `Fusionado en ${entityType || "tu universo"} (coherencia)`;
    case "EntryDeleted":
      return `Borraste una entrada de ${entityType || "tu universo"}`;
    case "DocumentGenerated": {
      const kind = (p.kind as string) ?? "documento";
      return `Generaste un ${kind}${p.template ? ` (${p.template})` : ""}`;
    }
    case "SuggestionAccepted":
      return `Aceptaste una sugerencia${p.title ? ` · ${p.title}` : ""}`;
    case "SuggestionRejected":
      return `Descartaste una sugerencia${p.title ? ` · ${p.title}` : ""}`;
    default:
      return event.event_type;
  }
}

function groupByDay(events: ActivityEvent[]): Array<{ day: string; events: ActivityEvent[] }> {
  const map = new Map<string, ActivityEvent[]>();
  for (const e of events) {
    const d = new Date(e.occurred_at);
    const key = d.toLocaleDateString(undefined, {
      weekday: "long",
      day: "numeric",
      month: "long",
    });
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(e);
  }
  return Array.from(map.entries()).map(([day, events]) => ({ day, events }));
}
