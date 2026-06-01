/**
 * Coherence engine change-log — the field-level diff feed (old→new per field,
 * with reason + source). Relocated from the retired UniverseDrawer's
 * "Trayectoria" tab, which was the only UI for this feed. Distinct from
 * ActivityPage's high-level event feed: this shows the low-level coherence
 * decisions (merges, ESCO links, field updates) attributed to their source.
 */
import { useQuery } from "@tanstack/react-query";
import {
  MessageSquare,
  User,
  FileText,
  Wand2,
  GitMerge,
  Plus,
  Pencil,
  Trash2,
} from "lucide-react";
import { api, type Page } from "@/shared/api";
import { Badge, Card, PageSkeleton, cn } from "@/ui";
import { GitHubIcon, LinkedInIcon } from "@/ui/icons";
import { queryKeys } from "@/shared/queryKeys";

interface ChangeLogRow {
  id?: string;
  entity_type: string;
  entity_id: string;
  change_type: string;
  field: string | null;
  old_value: unknown;
  new_value: unknown;
  reason: string | null;
  source: string;
  changed_at: string;
}

const SOURCE_META: Record<
  string,
  {
    label: string;
    Icon: React.ComponentType<{ size?: number }>;
    tone: "leaf" | "sunbeam" | "stone";
  }
> = {
  agent_chat: { label: "Agente", Icon: MessageSquare, tone: "leaf" },
  manual: { label: "Manual", Icon: User, tone: "stone" },
  github: { label: "GitHub", Icon: GitHubIcon, tone: "stone" },
  linkedin: { label: "LinkedIn", Icon: LinkedInIcon, tone: "stone" },
  linkedin_dma: { label: "LinkedIn DMA", Icon: LinkedInIcon, tone: "stone" },
  linkedin_brightdata: { label: "LinkedIn BD", Icon: LinkedInIcon, tone: "stone" },
  linkedin_zip: { label: "LinkedIn ZIP", Icon: LinkedInIcon, tone: "stone" },
  pdf: { label: "PDF", Icon: FileText, tone: "stone" },
  cv_generation: { label: "CV", Icon: Wand2, tone: "sunbeam" },
};

const CHANGE_ICON: Record<string, typeof Plus> = {
  create: Plus,
  created: Plus,
  insert: Plus,
  update: Pencil,
  updated: Pencil,
  patch: Pencil,
  merge: GitMerge,
  merged: GitMerge,
  delete: Trash2,
  deleted: Trash2,
};

function groupByDay(rows: ChangeLogRow[]): Array<{ day: string; rows: ChangeLogRow[] }> {
  const map = new Map<string, ChangeLogRow[]>();
  for (const r of rows) {
    const d = new Date(r.changed_at);
    const key = d.toLocaleDateString(undefined, {
      weekday: "long",
      day: "numeric",
      month: "long",
    });
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(r);
  }
  return Array.from(map.entries()).map(([day, rows]) => ({ day, rows }));
}

export function CoherenceChangesFeed() {
  const changes = useQuery({
    queryKey: queryKeys.coherence.changes,
    queryFn: () => api<Page<ChangeLogRow>>("/api/v1/coherence/changes?limit=50"),
  });

  if (changes.isLoading) return <PageSkeleton />;
  const rows = changes.data?.items ?? [];
  if (rows.length === 0) {
    return (
      <Card tone="glass" padding="lg" className="text-center space-y-2">
        <h3 className="text-heading-sm font-medium tracking-tight">Sin cambios de coherencia</h3>
        <p className="text-sm text-stone max-w-md mx-auto">
          Cuando el motor de coherencia fusione, enlace (ESCO) o actualice campos
          de tus entidades, cada decisión aparecerá aquí con su origen.
        </p>
      </Card>
    );
  }
  const groups = groupByDay(rows);
  return (
    <div className="flex flex-col gap-6">
      {groups.map((g) => (
        <section key={g.day}>
          <h3 className="text-[11px] uppercase tracking-wider text-stone font-medium mb-3 capitalize sticky top-16 bg-canvas/80 backdrop-blur-md py-1 z-10">
            {g.day}
          </h3>
          <ol className="relative space-y-0.5">
            <span aria-hidden className="absolute left-4 top-3 bottom-3 w-px bg-ink/8 -z-10" />
            {g.rows.map((r, i) => {
              const source = SOURCE_META[r.source] ?? {
                label: r.source,
                Icon: User,
                tone: "stone" as const,
              };
              const ChangeIcon = CHANGE_ICON[r.change_type] ?? Pencil;
              const time = new Date(r.changed_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              });
              return (
                <li key={r.id ?? i} className="flex items-start gap-3">
                  <span
                    aria-hidden
                    className={cn(
                      "shrink-0 w-8 h-8 rounded-full inline-flex items-center justify-center relative z-10 mt-1",
                      source.tone === "leaf" && "bg-leaf-soft text-leaf-ink",
                      source.tone === "sunbeam" && "bg-sunbeam-soft text-sunbeam-ink",
                      source.tone === "stone" && "bg-canvas border border-ink/10 text-stone",
                    )}
                  >
                    <source.Icon size={13} />
                  </span>
                  <Card padding="sm" tone="surface" className="flex-1 min-w-0 mb-2">
                    <div className="flex items-center gap-2 flex-wrap text-xs">
                      <span className="inline-flex items-center gap-1 text-ink font-medium capitalize">
                        <ChangeIcon size={12} className="text-stone" />
                        {r.change_type}
                      </span>
                      <span className="text-stone">{r.entity_type}</span>
                      {r.field && (
                        <span className="text-stone">· {r.field.replace(/_/g, " ")}</span>
                      )}
                      <Badge tone="stone" size="sm" className="ml-auto">
                        {source.label}
                      </Badge>
                      <span className="text-stone tabular-nums">{time}</span>
                    </div>
                    {r.field && r.old_value !== r.new_value && (
                      <div className="text-xs text-stone mt-1.5">
                        <span className="line-through" title={String(r.old_value ?? "")}>
                          {String(r.old_value ?? "—")}
                        </span>{" "}
                        <span>→</span>{" "}
                        <span className="font-medium text-ink">{String(r.new_value ?? "—")}</span>
                      </div>
                    )}
                    {r.reason && (
                      <p className="text-[11px] text-stone italic mt-1">{r.reason}</p>
                    )}
                  </Card>
                </li>
              );
            })}
          </ol>
        </section>
      ))}
    </div>
  );
}
