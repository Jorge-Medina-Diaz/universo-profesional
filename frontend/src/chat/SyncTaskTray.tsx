/**
 * Floating tray that surfaces long-running integration syncs as live progress
 * cards. Polls the existing `/api/v1/integrations/sync-runs` endpoint every
 * 3s and renders any run that is in flight (or just finished) in the lower
 * right of the chat surface.
 *
 * Sprint C — first slice. Cancellation is not yet wired (would need a
 * server-side abort endpoint); the card auto-dismisses 8s after the run
 * finishes so the user gets a tangible "done" cue without manual cleanup.
 */
import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { useAuthStore } from "@/shared/api";
import { integrations } from "@/shared/api-extra";
import { ProgressCard } from "./cards/ProgressCard";
import type { ProgressStep } from "@/ui";
import { queryKeys } from "@/shared/queryKeys";

interface SyncRun {
  id: string;
  provider: string;
  started_at: string;
  finished_at: string | null;
  ok: boolean | null;
  items_created: number;
  items_updated: number;
  error: string | null;
  summary: Record<string, unknown> | null;
}

const PROVIDER_LABEL: Record<string, string> = {
  github: "GitHub",
  linkedin_dma: "LinkedIn",
  linkedin_brightdata: "LinkedIn (PRO)",
};

const RECENT_MS = 8_000;

export function SyncTaskTray() {
  const authed = !!useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: queryKeys.integrations.syncRuns,
    queryFn: () => integrations.syncRuns(5),
    enabled: authed,
    // Slow tick by default; we accelerate to 1.5s while a run is in flight.
    refetchInterval: (queryData) => {
      const data = (queryData as unknown as { state?: { data?: { runs?: SyncRun[] } } }).state
        ?.data;
      const runs = (data?.runs ?? []) as unknown as SyncRun[];
      const hasInFlight = runs.some((r) => r.finished_at == null);
      return hasInFlight ? 1500 : 10_000;
    },
    staleTime: 0,
  });
  const [hiddenIds, setHiddenIds] = useState<Set<string>>(new Set());

  const visible = useMemo<SyncRun[]>(() => {
    const runs = (query.data?.runs as unknown as SyncRun[]) ?? [];
    const now = Date.now();
    return runs
      .filter((r) => !hiddenIds.has(r.id))
      .filter((r) => {
        if (r.finished_at == null) return true;
        return now - new Date(r.finished_at).getTime() < RECENT_MS;
      })
      .slice(0, 3);
  }, [query.data, hiddenIds]);

  // Auto-dismiss finished runs after RECENT_MS. We also invalidate universe
  // queries when a run completes so the rest of the app reflects new entities.
  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    for (const r of visible) {
      if (r.finished_at) {
        const remaining = RECENT_MS - (Date.now() - new Date(r.finished_at).getTime());
        if (remaining > 0) {
          timers.push(
            setTimeout(() => {
              setHiddenIds((prev) => {
                const next = new Set(prev);
                next.add(r.id);
                return next;
              });
            }, remaining),
          );
        }
        if (r.ok) {
          qc.invalidateQueries({ queryKey: queryKeys.universe.all });
          qc.invalidateQueries({ queryKey: queryKeys.integrations.all });
        }
      }
    }
    return () => {
      timers.forEach(clearTimeout);
    };
  }, [visible, qc]);

  if (!authed || visible.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-30 flex flex-col gap-3 max-w-sm">
      <AnimatePresence>
        {visible.map((run) => (
          <motion.div
            key={run.id}
            initial={{ opacity: 0, y: 12, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.97 }}
            transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
          >
            <ProgressCard
              title={`Sincronizando ${PROVIDER_LABEL[run.provider] ?? run.provider}`}
              detail={
                run.finished_at && run.ok
                  ? `+${run.items_created} nuevos · ${run.items_updated} actualizados`
                  : run.error ?? undefined
              }
              state={
                run.finished_at == null
                  ? "running"
                  : run.ok
                    ? "done"
                    : "error"
              }
              errorMessage={run.error ?? undefined}
              steps={buildSteps(run)}
              dismissLabel={
                run.finished_at == null
                  ? "Cancelar (el worker sigue en segundo plano)"
                  : "Cerrar"
              }
              onDismiss={() => {
                // Hide immediately in the UI; persist a soft-cancel server-side
                // so future polls don't bring it back. The worker keeps going.
                setHiddenIds((prev) => {
                  const next = new Set(prev);
                  next.add(run.id);
                  return next;
                });
                void integrations.cancelSyncRun(run.id).catch(() => {
                  // Silent — the UI dismissal stands either way.
                });
              }}
            />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

/** Heuristic 3-step bar from the integration sync run shape we already have.
 *  Step 1: connect / fetch. Step 2: parse + dedup. Step 3: persist. */
function buildSteps(run: SyncRun): ProgressStep[] {
  const inFlight = run.finished_at == null;
  if (inFlight) {
    return [
      { id: "fetch", label: "Llamando al proveedor", status: "active" },
      { id: "parse", label: "Parseando + deduplicando", status: "pending" },
      { id: "persist", label: "Mergeando en tu universo", status: "pending" },
    ];
  }
  const status: ProgressStep["status"] = run.ok ? "done" : "error";
  return [
    { id: "fetch", label: "Llamando al proveedor", status: "done" },
    { id: "parse", label: "Parseando + deduplicando", status: "done" },
    { id: "persist", label: "Mergeando en tu universo", status },
  ];
}
