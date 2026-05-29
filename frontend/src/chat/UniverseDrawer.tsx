/**
 * Side drawer that surfaces the user's universe without leaving the chat.
 *
 * Four tabs: Estructura · Trayectoria · Sugerencias · Conexiones.
 * Vaul handles the slide-in animation; this file just owns the layout
 * and the Pirsch-styled chrome.
 */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Drawer } from "vaul";
import {
  X,
  MessageSquare,
  User,
  FileText,
  Wand2,
  GitMerge,
  Plus,
  Pencil,
  Trash2,
} from "lucide-react";
import { api, universe } from "@/shared/api";
import { Badge, cn } from "@/ui";
import { GitHubIcon, LinkedInIcon } from "@/ui/icons";
import { queryKeys } from "@/shared/queryKeys";

type Tab = "estructura" | "trayectoria" | "sugerencias" | "conexiones";

interface UniverseDrawerProps {
  open: boolean;
  onClose: () => void;
}

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "estructura", label: "Estructura" },
  { id: "trayectoria", label: "Trayectoria" },
  { id: "sugerencias", label: "Sugerencias" },
  { id: "conexiones", label: "Conexiones" },
];

export function UniverseDrawer({ open, onClose }: UniverseDrawerProps) {
  const [tab, setTab] = useState<Tab>("estructura");
  return (
    <Drawer.Root direction="right" open={open} onOpenChange={(v: boolean) => !v && onClose()}>
      <Drawer.Portal>
        <Drawer.Overlay className="fixed inset-0 bg-ink/30 backdrop-blur-sm z-40" />
        <Drawer.Content
          className="bg-canvas text-ink flex flex-col fixed inset-y-0 right-0 z-50 w-full sm:w-[440px] shadow-lift"
          aria-describedby={undefined}
        >
          <Drawer.Title className="sr-only">Universo</Drawer.Title>
          <div className="flex items-center justify-between px-5 py-4 border-b border-ink/8">
            <div className="flex items-center gap-2.5">
              <span aria-hidden className="inline-block w-7 h-7 rounded-full bg-leaf grid place-items-center text-[12px] font-medium text-ink">
                u
              </span>
              <h2 className="font-medium text-ink">Tu universo</h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Cerrar"
              className="w-9 h-9 rounded-full grid place-items-center text-stone hover:text-ink hover:bg-ink/[0.04] transition-colors"
            >
              <X size={18} />
            </button>
          </div>
          <div className="flex gap-1 px-3 pt-3 border-b border-ink/5">
            {TABS.map((t) => (
              <TabButton key={t.id} active={tab === t.id} onClick={() => setTab(t.id)}>
                {t.label}
              </TabButton>
            ))}
          </div>
          <div className="flex-1 overflow-y-auto p-5">
            {tab === "estructura" && <EstructuraTab />}
            {tab === "trayectoria" && <TrayectoriaTab />}
            {tab === "sugerencias" && <SugerenciasTab />}
            {tab === "conexiones" && <ConexionesTab />}
          </div>
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "relative text-xs px-3 py-2 rounded-t-lg transition-colors duration-180 ease-pirsch font-medium",
        active ? "text-ink" : "text-stone hover:text-ink",
      )}
    >
      {children}
      {active && (
        <span
          aria-hidden
          className="absolute left-2 right-2 -bottom-px h-[2px] bg-leaf rounded-full"
        />
      )}
    </button>
  );
}

function EstructuraTab() {
  const summary = useQuery({
    queryKey: queryKeys.universe.summary,
    queryFn: () => universe.summary(),
  });
  if (summary.isLoading) return <Skeleton />;
  if (!summary.data) return <p className="text-sm text-stone">Sin datos todavía.</p>;
  const counts = summary.data.counts ?? {};
  return (
    <div className="space-y-5">
      <div>
        <div className="text-xs uppercase tracking-wider text-stone mb-1.5">Headline</div>
        <div className="text-sm font-medium text-ink">{summary.data.headline ?? "—"}</div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {Object.entries(counts).map(([k, v]) => (
          <div key={k} className="rounded-card bg-surface p-3">
            <div className="text-xs text-stone capitalize">{k}</div>
            <div className="text-2xl font-medium text-ink leading-tight">{v as number}</div>
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-2 pt-2 border-t border-ink/5">
        <DrawerLink href="#/universe">Ver entidades</DrawerLink>
        <DrawerLink href="#/notes">Ver notas</DrawerLink>
        <DrawerLink href="#/cv/new">Generar CV</DrawerLink>
      </div>
    </div>
  );
}

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
    const key = d.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(r);
  }
  return Array.from(map.entries()).map(([day, rows]) => ({ day, rows }));
}

function TrayectoriaTab() {
  const changes = useQuery({
    queryKey: queryKeys.coherence.changes,
    queryFn: () => api<ChangeLogRow[]>("/api/v1/coherence/changes?limit=50"),
  });
  if (changes.isLoading) return <Skeleton />;
  const rows = changes.data ?? [];
  if (rows.length === 0)
    return <p className="text-sm text-stone">Sin cambios todavía.</p>;
  const groups = groupByDay(rows);
  return (
    <div className="space-y-5">
      {groups.map((g) => (
        <section key={g.day}>
          <h3 className="text-[11px] uppercase tracking-wider text-stone font-medium mb-2 capitalize">
            {g.day}
          </h3>
          <ol className="relative space-y-0.5">
            <span
              aria-hidden
              className="absolute left-3.5 top-2 bottom-2 w-px bg-ink/8 -z-10"
            />
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
                <li key={r.id ?? i} className="flex items-start gap-3 relative">
                  <span
                    aria-hidden
                    className={cn(
                      "shrink-0 w-7 h-7 rounded-full inline-flex items-center justify-center relative z-10 mt-0.5",
                      source.tone === "leaf" && "bg-leaf-soft text-leaf-ink",
                      source.tone === "sunbeam" && "bg-sunbeam-soft text-sunbeam-ink",
                      source.tone === "stone" && "bg-canvas border border-ink/10 text-stone",
                    )}
                  >
                    <source.Icon size={12} />
                  </span>
                  <div className="flex-1 min-w-0 pb-3">
                    <div className="flex items-center gap-2 flex-wrap text-xs">
                      <span className="inline-flex items-center gap-1 text-ink font-medium capitalize">
                        <ChangeIcon size={12} className="text-stone" />
                        {r.change_type}
                      </span>
                      <span className="text-stone">{r.entity_type}</span>
                      {r.field && (
                        <span className="text-stone">· {r.field.replace(/_/g, " ")}</span>
                      )}
                      <span className="ml-auto text-stone tabular-nums">{time}</span>
                    </div>
                    {r.field && r.old_value !== r.new_value && (
                      <div className="text-xs text-stone mt-1">
                        <span className="line-through truncate" title={String(r.old_value ?? "")}>
                          {String(r.old_value ?? "—")}
                        </span>{" "}
                        <span>→</span>{" "}
                        <span className="font-medium text-ink">
                          {String(r.new_value ?? "—")}
                        </span>
                      </div>
                    )}
                    {r.reason && (
                      <p className="text-[11px] text-stone italic mt-1">{r.reason}</p>
                    )}
                    <Badge tone="stone" size="sm" className="mt-1.5">
                      {source.label}
                    </Badge>
                  </div>
                </li>
              );
            })}
          </ol>
        </section>
      ))}
    </div>
  );
}

interface SuggestionRow {
  id: string;
  kind: string;
  title: string;
  body?: string | null;
  status: string;
}

function SugerenciasTab() {
  const sugs = useQuery({
    queryKey: queryKeys.suggestions.pending,
    queryFn: () => api<SuggestionRow[]>("/api/v1/universe/suggestions?status=pending"),
  });
  if (sugs.isLoading) return <Skeleton />;
  const rows = sugs.data ?? [];
  if (rows.length === 0)
    return <p className="text-sm text-stone">No hay sugerencias pendientes.</p>;
  return (
    <ul className="space-y-2">
      {rows.map((s) => (
        <li key={s.id} className="rounded-card bg-surface p-4 text-xs">
          <div className="flex items-start justify-between gap-2 mb-1">
            <div className="font-medium text-ink text-sm">{s.title}</div>
            <Badge tone="sunbeam" size="sm">
              {s.kind}
            </Badge>
          </div>
          {s.body && <div className="text-stone leading-relaxed">{s.body}</div>}
        </li>
      ))}
    </ul>
  );
}

function ConexionesTab() {
  return (
    <div className="space-y-2">
      <DrawerLink href="#/connections">GitHub · LinkedIn · PDF</DrawerLink>
      <DrawerLink href="#/mcp">MCP (Claude Code, Codex…)</DrawerLink>
      <DrawerLink href="#/settings">Ajustes</DrawerLink>
    </div>
  );
}

function DrawerLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className="block rounded-card bg-surface hover:bg-surface/70 px-4 py-3 text-sm text-ink transition-colors duration-180 ease-pirsch"
    >
      <span className="flex items-center justify-between">
        {children}
        <span aria-hidden className="text-stone">→</span>
      </span>
    </a>
  );
}

function Skeleton() {
  return (
    <div className="space-y-3" aria-hidden>
      <div className="h-4 w-32 bg-ink/[0.06] rounded animate-pulse" />
      <div className="h-20 bg-ink/[0.06] rounded-card animate-pulse" />
      <div className="h-20 bg-ink/[0.06] rounded-card animate-pulse" />
    </div>
  );
}
