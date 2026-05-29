/**
 * Reminders — full-page view of everything your universe needs attention on.
 *
 * The NotificationCenter bell shows the same data in a popover; this page is
 * the deep-link target the daily digest email points at, and gives more room
 * to read + act on a longer list.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Bell, Briefcase, Calendar, Check, RefreshCw, Mail } from "lucide-react";
import { account, universe, type ReminderRow } from "@/shared/api";
import { queryKeys } from "@/shared/queryKeys";
import {
  Badge,
  BellQuietIllustration,
  Button,
  Card,
  PageHeader,
  Reveal,
  Stagger,
  Surface,
  cn,
  toast,
} from "@/ui";

const KIND_META: Record<
  string,
  { label: string; tone: "amber" | "sunbeam" | "leaf" | "stone"; Icon: typeof AlertTriangle }
> = {
  cert_expiring: { label: "Certificación", tone: "amber", Icon: AlertTriangle },
  course_stale: { label: "Curso en pausa", tone: "stone", Icon: Calendar },
  job_followup: { label: "Seguimiento", tone: "sunbeam", Icon: Briefcase },
};

export function RemindersPage() {
  const qc = useQueryClient();

  const reminders = useQuery({
    queryKey: queryKeys.reminders.all,
    queryFn: () => universe.reminders.list(),
    staleTime: 30_000,
  });

  const prefs = useQuery({
    queryKey: ["notification-prefs"],
    queryFn: () => account.getNotificationPrefs(),
    staleTime: 60_000,
  });

  const scan = useMutation({
    mutationFn: () => universe.reminders.scan(),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: queryKeys.reminders.all });
      toast.success(
        r.created > 0 ? `${r.created} recordatorio(s) nuevo(s)` : "Todo al día",
        r.created > 0 ? undefined : "No encontramos nada nuevo que recordarte.",
      );
    },
    onError: (e) => toast.error("No pudimos escanear", (e as Error).message),
  });

  const dismiss = useMutation({
    mutationFn: (id: string) => universe.reminders.dismiss(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: queryKeys.reminders.all });
      const prev = qc.getQueryData<ReminderRow[]>(queryKeys.reminders.all);
      qc.setQueryData<ReminderRow[]>(queryKeys.reminders.all, (old) =>
        (old ?? []).filter((r) => r.id !== id),
      );
      return { prev };
    },
    onError: (e, _id, ctx) => {
      if (ctx?.prev) qc.setQueryData(queryKeys.reminders.all, ctx.prev);
      toast.error("No pudimos descartar el recordatorio", (e as Error).message);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: queryKeys.reminders.all }),
  });

  const toggleEmail = useMutation({
    mutationFn: (email_reminders: boolean) =>
      account.setNotificationPrefs({ email_reminders }),
    onSuccess: (p) => {
      qc.setQueryData(["notification-prefs"], p);
      toast.success(
        p.email_reminders ? "Emails activados" : "Emails desactivados",
        p.email_reminders
          ? "Te avisaremos por email cuando haya recordatorios."
          : "Seguirás viéndolos aquí y en la campana.",
      );
    },
    onError: (e) => toast.error("No pudimos guardar la preferencia", (e as Error).message),
  });

  const list = reminders.data ?? [];

  return (
    <Surface width="md" spacing="md">
      <PageHeader
        eyebrow="Mantenimiento"
        title="Recordatorios"
        subtitle="Lo que tu universo necesita revisar: certificaciones por caducar, cursos en pausa y más."
        actions={
          <Button
            variant="outline"
            onClick={() => scan.mutate()}
            loading={scan.isPending}
            leadingIcon={<RefreshCw size={14} />}
          >
            {scan.isPending ? "Escaneando" : "Escanear ahora"}
          </Button>
        }
      />

      <Stagger className="flex flex-col gap-4 md:gap-5" delayStep={0.05}>
        {/* Email preference */}
        <Card padding="md" tone="glass">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <span
                aria-hidden
                className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-canvas text-ink shrink-0"
              >
                <Mail size={16} />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-medium text-ink">Resumen por email</p>
                <p className="text-xs text-stone">
                  Un email diario cuando haya recordatorios pendientes.
                </p>
              </div>
            </div>
            <Toggle
              checked={prefs.data?.email_reminders ?? true}
              disabled={prefs.isLoading || toggleEmail.isPending}
              onChange={(v) => toggleEmail.mutate(v)}
            />
          </div>
        </Card>

        {reminders.isLoading ? (
          <Card padding="lg">
            <p className="text-sm text-stone text-center py-6">Cargando…</p>
          </Card>
        ) : list.length === 0 ? (
          <Reveal>
            <Card padding="lg" className="text-center space-y-3 py-10">
              <BellQuietIllustration className="mx-auto" width={160} height={116} />
              <p className="text-heading-sm font-display text-ink">Sin recordatorios</p>
              <p className="text-sm text-stone max-w-sm mx-auto">
                Cuando algo necesite tu atención —una certificación a punto de caducar,
                un curso parado— aparecerá aquí.
              </p>
            </Card>
          </Reveal>
        ) : (
          <Card padding="none" className="overflow-hidden">
            <ul className="divide-y divide-hairline">
              {list.map((r) => {
                const meta = KIND_META[r.kind] ?? {
                  label: r.kind,
                  tone: "stone" as const,
                  Icon: Bell,
                };
                return (
                  <li
                    key={r.id}
                    className="group flex items-start gap-3 px-4 md:px-5 py-4 hover:bg-surface transition-colors"
                  >
                    <span
                      aria-hidden
                      className={cn(
                        "inline-flex items-center justify-center w-9 h-9 rounded-full shrink-0",
                        meta.tone === "amber" && "bg-sunbeam-soft text-sunbeam-ink",
                        meta.tone === "sunbeam" && "bg-sunbeam-soft text-sunbeam-ink",
                        meta.tone === "leaf" && "bg-leaf-soft text-leaf-ink",
                        meta.tone === "stone" && "bg-ink/[0.04] text-stone",
                      )}
                    >
                      <meta.Icon size={15} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-ink leading-tight">
                          {r.title}
                        </span>
                        <Badge tone={meta.tone} size="sm">
                          {meta.label}
                        </Badge>
                      </div>
                      <p className="text-sm text-stone mt-1 leading-relaxed">{r.body}</p>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      loading={dismiss.isPending && dismiss.variables === r.id}
                      onClick={() => dismiss.mutate(r.id)}
                      leadingIcon={<Check size={13} />}
                    >
                      Hecho
                    </Button>
                  </li>
                );
              })}
            </ul>
          </Card>
        )}
      </Stagger>
    </Surface>
  );
}

function Toggle({
  checked,
  disabled,
  onChange,
}: {
  checked: boolean;
  disabled?: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-180 disabled:opacity-50",
        checked ? "bg-leaf" : "bg-ink/15",
      )}
    >
      <span
        className={cn(
          "inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform duration-180",
          checked ? "translate-x-[22px]" : "translate-x-0.5",
        )}
      />
    </button>
  );
}
