/**
 * Subtle banner that surfaces pending reminders inside the chat surface.
 *
 * When the user has 1+ active reminders we show a one-line nudge with a CTA
 * that injects a chat prompt — the agent then renders them with the existing
 * `preview_list(kind='reminders', …)` action. Pure A2UI flow: this widget
 * is a launcher, not a UI for the reminders themselves.
 *
 * Hidden once dismissed or once the user opens them in chat (per-session).
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "motion/react";
import { BellRing, X, ArrowRight } from "lucide-react";
import { universe, useAuthStore } from "@/shared/api";
import { Badge, cn } from "@/ui";
import { queryKeys } from "@/shared/queryKeys";

const DISMISS_KEY = "cvs-saas-reminders-banner-dismissed";

function isDismissedToday(): boolean {
  try {
    const raw = sessionStorage.getItem(DISMISS_KEY);
    if (!raw) return false;
    const { date } = JSON.parse(raw) as { date: string };
    return date === new Date().toISOString().slice(0, 10);
  } catch {
    return false;
  }
}

function markDismissed(): void {
  try {
    sessionStorage.setItem(
      DISMISS_KEY,
      JSON.stringify({ date: new Date().toISOString().slice(0, 10) }),
    );
  } catch {
    /* ignore */
  }
}

export function RemindersBanner({
  onAsk,
}: {
  /** Called when the user clicks the CTA. Should inject a prompt into chat. */
  onAsk: () => void;
}) {
  const authed = !!useAuthStore((s) => s.accessToken);
  const [dismissed, setDismissed] = useState(isDismissedToday);
  const remindersQ = useQuery({
    queryKey: queryKeys.reminders.pending,
    queryFn: () => universe.reminders.list(),
    enabled: authed && !dismissed,
    staleTime: 5 * 60_000,
  });
  const count = remindersQ.data?.length ?? 0;
  if (dismissed || count === 0) return null;

  // Count overdue separately to colour the banner more urgently.
  const now = Date.now();
  const overdue = (remindersQ.data ?? []).filter(
    (r) => r.due_at && new Date(r.due_at).getTime() < now,
  ).length;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
        className={cn(
          "flex items-center gap-3 rounded-card px-3 py-2 mb-2 mx-auto max-w-3xl text-sm",
          overdue > 0
            ? "bg-sunbeam-soft/70 text-sunbeam-ink border border-sunbeam/30"
            : "bg-leaf-soft/60 text-leaf-ink border border-leaf/20",
        )}
        role="status"
      >
        <span
          aria-hidden
          className={cn(
            "inline-flex items-center justify-center w-7 h-7 rounded-full shrink-0",
            overdue > 0 ? "bg-sunbeam text-ink" : "bg-leaf text-ink",
          )}
        >
          <BellRing size={14} />
        </span>
        <div className="flex-1 min-w-0 flex items-center gap-2 flex-wrap">
          <span className="font-medium leading-tight">
            Tienes{" "}
            <Badge tone={overdue > 0 ? "amber" : "leaf"} size="sm">
              {count}
            </Badge>{" "}
            {count === 1 ? "recordatorio" : "recordatorios"}
            {overdue > 0 ? ` (${overdue} vencido${overdue > 1 ? "s" : ""})` : ""}
          </span>
        </div>
        <button
          type="button"
          onClick={() => {
            markDismissed();
            setDismissed(true);
            onAsk();
          }}
          className="inline-flex items-center gap-1 text-xs font-medium hover:underline underline-offset-4 shrink-0"
        >
          Revisar en el chat
          <ArrowRight size={12} />
        </button>
        <button
          type="button"
          aria-label="Ocultar"
          onClick={() => {
            markDismissed();
            setDismissed(true);
          }}
          className="w-6 h-6 inline-flex items-center justify-center rounded-full hover:bg-ink/[0.05] transition-colors shrink-0"
        >
          <X size={12} />
        </button>
      </motion.div>
    </AnimatePresence>
  );
}
