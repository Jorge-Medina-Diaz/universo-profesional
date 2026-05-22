/**
 * Topbar bell — opens a popover listing pending reminders.
 *
 * Reminders are server-generated nudges (cert expiring, course stale, etc.).
 * The agent doesn't surface them automatically; this widget gives the user
 * a sticky, persistent entry point that doesn't depend on the chat.
 */
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import {
  Bell,
  Check,
  AlertTriangle,
  Calendar,
  RefreshCw,
} from "lucide-react";
import { universe, type ReminderRow } from "@/shared/api";
import { Badge, BellQuietIllustration, Button, cn } from "@/ui";

const KIND_META: Record<string, { label: string; tone: "amber" | "sunbeam" | "leaf" | "stone"; Icon: typeof AlertTriangle }> = {
  cert_expiring: { label: "Certificación", tone: "amber", Icon: AlertTriangle },
  course_stale: { label: "Curso en pausa", tone: "stone", Icon: Calendar },
};

export function RemindersBell() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const reminders = useQuery({
    queryKey: ["reminders"],
    queryFn: () => universe.reminders.list(),
    refetchOnWindowFocus: false,
    staleTime: 60_000,
  });

  const dismiss = useMutation({
    mutationFn: (id: string) => universe.reminders.dismiss(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reminders"] }),
  });

  const scan = useMutation({
    mutationFn: () => universe.reminders.scan(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reminders"] }),
  });

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        !buttonRef.current?.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const count = reminders.data?.length ?? 0;

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Recordatorios (${count})`}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="relative inline-flex items-center justify-center w-9 h-9 rounded-full text-stone hover:text-ink hover:bg-surface transition-colors duration-180 ease-pirsch"
      >
        <Bell size={16} />
        {count > 0 && (
          <span
            aria-hidden
            className="absolute -top-0.5 -right-0.5 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-sunbeam text-sunbeam-ink text-[10px] font-bold"
          >
            {count > 9 ? "9+" : count}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            ref={popoverRef}
            role="dialog"
            aria-label="Recordatorios"
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.97 }}
            transition={{ duration: 0.18, ease: [0.2, 0.8, 0.2, 1] }}
            className="absolute right-0 top-full mt-2 w-[340px] max-w-[calc(100vw-2rem)] rounded-card bg-canvas shadow-lift border border-ink/8 z-50 overflow-hidden"
          >
            <header className="flex items-center justify-between px-4 py-3 border-b border-ink/5">
              <h2 className="font-medium text-ink">Recordatorios</h2>
              <button
                type="button"
                onClick={() => scan.mutate()}
                disabled={scan.isPending}
                aria-label="Re-escanear"
                className="inline-flex items-center gap-1.5 text-xs text-stone hover:text-ink transition-colors disabled:opacity-50"
              >
                <RefreshCw
                  size={12}
                  className={cn(scan.isPending && "animate-spin")}
                />
                {scan.isPending ? "Escaneando" : "Escanear"}
              </button>
            </header>
            <div className="max-h-[60vh] overflow-y-auto">
              {reminders.isLoading ? (
                <div className="px-4 py-6 text-center text-sm text-stone">Cargando…</div>
              ) : count === 0 ? (
                <EmptyState />
              ) : (
                <ul className="divide-y divide-ink/5">
                  {reminders.data!.map((r) => (
                    <ReminderItem
                      key={r.id}
                      reminder={r}
                      onDismiss={() => dismiss.mutate(r.id)}
                      dismissing={dismiss.isPending && dismiss.variables === r.id}
                    />
                  ))}
                </ul>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="px-6 py-6 text-center space-y-2">
      <BellQuietIllustration className="mx-auto" width={140} height={100} />
      <p className="text-sm text-ink font-medium">Sin recordatorios</p>
      <p className="text-xs text-stone">
        Cuando algo necesite tu atención (certificación a punto de expirar,
        curso parado…) aparecerá aquí.
      </p>
    </div>
  );
}

function ReminderItem({
  reminder,
  onDismiss,
  dismissing,
}: {
  reminder: ReminderRow;
  onDismiss: () => void;
  dismissing: boolean;
}) {
  const meta = KIND_META[reminder.kind] ?? {
    label: reminder.kind,
    tone: "stone" as const,
    Icon: Bell,
  };
  const Icon = meta.Icon;
  const due = new Date(reminder.due_at);
  const dueLabel = formatDue(due);
  return (
    <li className="group px-4 py-3 hover:bg-surface transition-colors duration-180 ease-pirsch">
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
          <Icon size={14} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-ink leading-tight">
              {reminder.title}
            </span>
            <Badge tone={meta.tone} size="sm">
              {meta.label}
            </Badge>
          </div>
          <p className="text-xs text-stone mt-1 leading-relaxed">{reminder.body}</p>
          <div className="flex items-center justify-between gap-2 mt-2">
            <span className="text-[11px] text-stone">{dueLabel}</span>
            <Button
              size="sm"
              variant="ghost"
              loading={dismissing}
              onClick={onDismiss}
              leadingIcon={!dismissing && <Check size={12} />}
              className="px-2 py-1 h-7 text-[11px]"
            >
              {dismissing ? "" : "Hecho"}
            </Button>
          </div>
        </div>
      </div>
    </li>
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
