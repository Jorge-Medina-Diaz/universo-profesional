/**
 * Unified notification center — bell icon in the header that opens a popover
 * with 3 sections: Reminders, Suggestions, Job alerts.
 *
 * Each section aggregates server-side signals into one entry point:
 *   - Reminders   → certs expiring, courses stale ([reminders] table).
 *   - Suggestions → universe gaps detected by `GenerateSuggestions`.
 *   - Job alerts  → kanban jobs that need attention (no match score with a
 *                   rich JD, or interested >14d without movement).
 *
 * Replaces the older `RemindersBell` (kept around for retro-compat but
 * unmounted from the Layout). Each item carries an action: dismiss for
 * reminders, accept/reject for suggestions, jump-to-page for job alerts.
 */
import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import {
  Bell,
  Check,
  AlertTriangle,
  Calendar,
  RefreshCw,
  Sparkles,
  Briefcase,
  X,
} from "lucide-react";
import { universe, jobs, type ReminderRow, type JobRow } from "@/shared/api";
import { liveProfile, type Suggestion } from "@/shared/api-extra";
import { Badge, BellQuietIllustration, Button, cn } from "@/ui";
import { queryKeys } from "@/shared/queryKeys";
import { useClickOutside } from "@/shared/useClickOutside";
import { useEscapeKey } from "@/shared/useEscapeKey";

type SectionKey = "reminders" | "suggestions" | "jobs";

const REMINDER_KIND_META: Record<
  string,
  { label: string; tone: "amber" | "sunbeam" | "leaf" | "stone"; Icon: typeof AlertTriangle }
> = {
  cert_expiring: { label: "Certificación", tone: "amber", Icon: AlertTriangle },
  course_stale: { label: "Curso en pausa", tone: "stone", Icon: Calendar },
};

interface JobAlert {
  id: string;
  title: string;
  company: string | null;
  reason: "no_score" | "stale_interested";
  href: string;
}

function deriveJobAlerts(rows: JobRow[]): JobAlert[] {
  const alerts: JobAlert[] = [];
  const now = Date.now();
  for (const j of rows) {
    if (j.status === "archived" || j.status === "rejected") continue;
    const hasJD = (j.description_raw ?? "").length > 30;
    if (hasJD && j.match_score == null) {
      alerts.push({
        id: j.id,
        title: j.title || "Sin título",
        company: j.company_name,
        reason: "no_score",
        href: "#/jobs",
      });
      continue;
    }
    if (j.status === "interested" && j.created_at) {
      const ageDays = (now - new Date(j.created_at).getTime()) / (1000 * 60 * 60 * 24);
      if (ageDays > 14) {
        alerts.push({
          id: j.id,
          title: j.title || "Sin título",
          company: j.company_name,
          reason: "stale_interested",
          href: "#/jobs",
        });
      }
    }
  }
  return alerts.slice(0, 5);
}

export function NotificationCenter() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [section, setSection] = useState<SectionKey>("reminders");
  const wrapperRef = useRef<HTMLDivElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  const reminders = useQuery({
    queryKey: queryKeys.reminders.all,
    queryFn: () => universe.reminders.list(),
    refetchOnWindowFocus: false,
    staleTime: 60_000,
  });
  const suggestions = useQuery({
    queryKey: queryKeys.suggestions.pending,
    queryFn: () => liveProfile.suggestions.list("pending"),
    refetchOnWindowFocus: false,
    staleTime: 60_000,
  });
  const jobsQ = useQuery({
    queryKey: queryKeys.jobs.all,
    queryFn: () => jobs.list(),
    refetchOnWindowFocus: false,
    staleTime: 60_000,
  });
  const jobAlerts = useMemo(
    () => deriveJobAlerts(jobsQ.data ?? []),
    [jobsQ.data],
  );

  const dismissReminder = useMutation({
    mutationFn: (id: string) => universe.reminders.dismiss(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.reminders.all }),
  });
  const scanReminders = useMutation({
    mutationFn: () => universe.reminders.scan(),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.reminders.all }),
  });
  const actSuggestion = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "accept" | "reject" }) =>
      liveProfile.suggestions.act(id, action),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.suggestions.all }),
  });

  useClickOutside(wrapperRef, () => setOpen(false), open);

  useEscapeKey(() => setOpen(false), open);

  const counts = {
    reminders: reminders.data?.length ?? 0,
    suggestions: suggestions.data?.length ?? 0,
    jobs: jobAlerts.length,
  };
  const total = counts.reminders + counts.suggestions + counts.jobs;

  return (
    <div className="relative" ref={wrapperRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Notificaciones (${total})`}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="relative inline-flex items-center justify-center w-9 h-9 rounded-full text-stone hover:text-ink hover:bg-surface transition-colors duration-180 ease-pirsch"
      >
        <Bell size={16} />
        {total > 0 && (
          <span
            aria-hidden
            className="absolute -top-0.5 -right-0.5 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-sunbeam text-sunbeam-ink text-[10px] font-bold"
          >
            {total > 9 ? "9+" : total}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            ref={popoverRef}
            role="dialog"
            aria-label="Notificaciones"
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.97 }}
            transition={{ duration: 0.18, ease: [0.2, 0.8, 0.2, 1] }}
            className="absolute right-0 top-full mt-2 w-[380px] max-w-[calc(100vw-2rem)] rounded-card bg-canvas shadow-lift border border-ink/8 z-50 overflow-hidden"
          >
            <header className="flex items-center justify-between gap-2 px-4 py-3 border-b border-ink/5">
              <h2 className="font-medium text-ink">Notificaciones</h2>
              {section === "reminders" && (
                <button
                  type="button"
                  onClick={() => scanReminders.mutate()}
                  disabled={scanReminders.isPending}
                  aria-label="Re-escanear"
                  className="inline-flex items-center gap-1.5 text-xs text-stone hover:text-ink transition-colors disabled:opacity-50"
                >
                  <RefreshCw size={12} className={cn(scanReminders.isPending && "animate-spin")} />
                  {scanReminders.isPending ? "Escaneando" : "Escanear"}
                </button>
              )}
            </header>
            <div role="tablist" className="flex items-center gap-0.5 px-2 pt-2 text-xs">
              <SectionTab
                active={section === "reminders"}
                count={counts.reminders}
                Icon={Bell}
                label="Recordatorios"
                onClick={() => setSection("reminders")}
              />
              <SectionTab
                active={section === "suggestions"}
                count={counts.suggestions}
                Icon={Sparkles}
                label="Sugerencias"
                onClick={() => setSection("suggestions")}
              />
              <SectionTab
                active={section === "jobs"}
                count={counts.jobs}
                Icon={Briefcase}
                label="Ofertas"
                onClick={() => setSection("jobs")}
              />
            </div>
            <div className="max-h-[60vh] overflow-y-auto">
              {section === "reminders" && (
                <>
                  <ReminderList
                    data={reminders.data}
                    loading={reminders.isLoading}
                    onDismiss={(id) => dismissReminder.mutate(id)}
                    dismissingId={
                      dismissReminder.isPending ? dismissReminder.variables ?? null : null
                    }
                  />
                  <a
                    href="#/reminders"
                    onClick={() => setOpen(false)}
                    className="block px-4 py-2.5 text-center text-xs font-medium text-stone hover:text-ink border-t border-ink/5 transition-colors"
                  >
                    Ver todos los recordatorios →
                  </a>
                </>
              )}
              {section === "suggestions" && (
                <SuggestionList
                  data={suggestions.data}
                  loading={suggestions.isLoading}
                  onAct={(id, action) => actSuggestion.mutate({ id, action })}
                  acting={actSuggestion.isPending}
                />
              )}
              {section === "jobs" && (
                <JobAlertList data={jobAlerts} loading={jobsQ.isLoading} />
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function SectionTab({
  active,
  count,
  label,
  Icon,
  onClick,
}: {
  active: boolean;
  count: number;
  label: string;
  Icon: typeof Bell;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-tag transition-colors duration-180 ease-pirsch",
        active ? "bg-surface text-ink font-medium" : "text-stone hover:text-ink",
      )}
    >
      <Icon size={12} />
      <span>{label}</span>
      {count > 0 && (
        <span className={cn(
          "min-w-[16px] h-[16px] inline-flex items-center justify-center px-1 rounded-full text-[10px] font-bold",
          active ? "bg-sunbeam text-sunbeam-ink" : "bg-black/[0.06] text-stone",
        )}>
          {count}
        </span>
      )}
    </button>
  );
}

function ReminderList({
  data,
  loading,
  onDismiss,
  dismissingId,
}: {
  data: ReminderRow[] | undefined;
  loading: boolean;
  onDismiss: (id: string) => void;
  dismissingId: string | null;
}) {
  if (loading) return <div className="px-4 py-6 text-center text-sm text-stone">Cargando…</div>;
  const list = data ?? [];
  if (list.length === 0) {
    return (
      <div className="px-6 py-6 text-center space-y-2">
        <BellQuietIllustration className="mx-auto" width={140} height={100} />
        <p className="text-sm text-ink font-medium">Sin recordatorios</p>
        <p className="text-xs text-stone">
          Cuando algo necesite tu atención aparecerá aquí.
        </p>
      </div>
    );
  }
  return (
    <ul className="divide-y divide-ink/5">
      {list.map((r) => {
        const meta = REMINDER_KIND_META[r.kind] ?? {
          label: r.kind,
          tone: "stone" as const,
          Icon: Bell,
        };
        const due = new Date(r.due_at);
        return (
          <li key={r.id} className="group px-4 py-3 hover:bg-surface transition-colors">
            <div className="flex items-start gap-3">
              <span
                aria-hidden
                className={cn(
                  "inline-flex items-center justify-center w-9 h-9 rounded-full shrink-0",
                  meta.tone === "amber" && "bg-sunbeam-soft text-sunbeam-ink",
                  meta.tone === "sunbeam" && "bg-sunbeam-soft text-sunbeam-ink",
                  meta.tone === "leaf" && "bg-leaf-soft text-leaf-ink",
                  meta.tone === "stone" && "bg-black/[0.04] text-stone",
                )}
              >
                <meta.Icon size={14} />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-ink leading-tight">{r.title}</span>
                  <Badge tone={meta.tone} size="sm">
                    {meta.label}
                  </Badge>
                </div>
                <p className="text-xs text-stone mt-1 leading-relaxed">{r.body}</p>
                <div className="flex items-center justify-between gap-2 mt-2">
                  <span className="text-[11px] text-stone">{formatDue(due)}</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    loading={dismissingId === r.id}
                    onClick={() => onDismiss(r.id)}
                    leadingIcon={dismissingId !== r.id && <Check size={12} />}
                    className="px-2 py-1 h-7 text-[11px]"
                  >
                    {dismissingId === r.id ? "" : "Hecho"}
                  </Button>
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function SuggestionList({
  data,
  loading,
  onAct,
  acting,
}: {
  data: Suggestion[] | undefined;
  loading: boolean;
  onAct: (id: string, action: "accept" | "reject") => void;
  acting: boolean;
}) {
  if (loading) return <div className="px-4 py-6 text-center text-sm text-stone">Cargando…</div>;
  const list = (data ?? []).slice(0, 6);
  if (list.length === 0) {
    return (
      <div className="px-6 py-6 text-center space-y-2">
        <Sparkles size={36} className="mx-auto text-stone" />
        <p className="text-sm text-ink font-medium">Sin sugerencias</p>
        <p className="text-xs text-stone">
          Cuando el agente detecte gaps en tu universo, los propondrá aquí.
        </p>
      </div>
    );
  }
  return (
    <ul className="divide-y divide-ink/5">
      {list.map((s) => (
        <li key={s.id} className="group px-4 py-3 hover:bg-surface transition-colors">
          <div className="flex items-start gap-3">
            <span className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-leaf-soft text-leaf-ink shrink-0">
              <Sparkles size={14} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-ink leading-tight">{s.title}</span>
                <Badge tone="stone" size="sm">
                  {s.kind}
                </Badge>
              </div>
              {s.payload && (
                <p className="text-xs text-stone mt-1 leading-relaxed line-clamp-2">
                  {Object.entries(s.payload as Record<string, unknown>)
                    .slice(0, 2)
                    .map(([k, v]) => `${k}: ${String(v)}`)
                    .join(" · ")}
                </p>
              )}
              <div className="flex items-center justify-end gap-2 mt-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onAct(s.id, "reject")}
                  disabled={acting}
                  leadingIcon={<X size={12} />}
                  className="px-2 py-1 h-7 text-[11px]"
                >
                  Rechazar
                </Button>
                <Button
                  size="sm"
                  onClick={() => onAct(s.id, "accept")}
                  disabled={acting}
                  leadingIcon={<Check size={12} />}
                  className="px-2 py-1 h-7 text-[11px]"
                >
                  Aceptar
                </Button>
              </div>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}

function JobAlertList({ data, loading }: { data: JobAlert[]; loading: boolean }) {
  if (loading) return <div className="px-4 py-6 text-center text-sm text-stone">Cargando…</div>;
  if (data.length === 0) {
    return (
      <div className="px-6 py-6 text-center space-y-2">
        <Briefcase size={36} className="mx-auto text-stone" />
        <p className="text-sm text-ink font-medium">Tu pipeline está limpio</p>
        <p className="text-xs text-stone">
          Cuando una oferta se quede parada o necesite atención, aparecerá aquí.
        </p>
      </div>
    );
  }
  return (
    <ul className="divide-y divide-ink/5">
      {data.map((a) => (
        <li key={a.id}>
          <a
            href={a.href}
            className="group flex items-start gap-3 px-4 py-3 hover:bg-surface transition-colors"
          >
            <span className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-sunbeam-soft text-sunbeam-ink shrink-0">
              <Briefcase size={14} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-ink leading-tight truncate">
                {a.title}
              </div>
              {a.company && (
                <div className="text-xs text-stone truncate">{a.company}</div>
              )}
              <p className="text-[11px] text-stone mt-1">
                {a.reason === "no_score"
                  ? "Sin match calculado todavía"
                  : "Lleva >14 días en 'Interesado' sin moverse"}
              </p>
            </div>
          </a>
        </li>
      ))}
    </ul>
  );
}

function formatDue(due: Date): string {
  const now = new Date();
  const diffMs = due.getTime() - now.getTime();
  const days = Math.round(diffMs / (1000 * 60 * 60 * 24));
  if (days < -1) return `Hace ${-days} días`;
  if (days === -1) return "Ayer";
  if (days === 0) return "Hoy";
  if (days === 1) return "Mañana";
  if (days < 30) return `En ${days} días`;
  return due.toLocaleDateString();
}
