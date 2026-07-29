import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useChatState } from "@/chat/state";
import { queryKeys } from "@/shared/queryKeys";
import { AnimatePresence, motion } from "motion/react";
import {
  Plus,
  Briefcase,
  RefreshCw,
} from "lucide-react";
import { jobs, type JobRow, type JobStatus } from "@/shared/api";
import { usePullToRefresh } from "@/shared/usePullToRefresh";
import { usePageContext } from "@/shared/usePageContext";
import { AgentPageBridge } from "@/chat/useAgentPageBridge";
import {
  Badge,
  Button,
  Card,
  Field,
  Input,
  PageHeader,
  PageSkeleton,
  Reveal,
  Stagger,
  Surface,
  Textarea,
  toast,
} from "@/ui";
import { AutopilotRunner } from "./_jobs/AutopilotRunner";
import { COLUMNS, type DropAnchor } from "./_jobs/columns";
import {
  JobListRow,
  KanbanColumn,
  ViewTab,
} from "./_jobs/BoardParts";

type ViewMode = "kanban" | "list";


/** Compute a new fractional position for an item dropped at index `dropIndex`
 *  inside `column` (the column items already excluding the dragged one). */
function computePosition(column: JobRow[], dropIndex: number): number {
  const safeIndex = Math.max(0, Math.min(dropIndex, column.length));
  const getPos = (i: number) =>
    column[i]?.position ?? (column[i]?.created_at ? -Date.parse(column[i]!.created_at!) : 0);
  if (column.length === 0) return 0;
  if (safeIndex === 0) {
    return getPos(0) - 1;
  }
  if (safeIndex >= column.length) {
    return getPos(column.length - 1) + 1;
  }
  return (getPos(safeIndex - 1) + getPos(safeIndex)) / 2;
}

export function JobsPage() {
  const qc = useQueryClient();
  const query = useQuery({ queryKey: queryKeys.jobs.all, queryFn: () => jobs.list() });
  const [view, setView] = useState<ViewMode>("kanban");
  const [creating, setCreating] = useState(false);
  const [autopilotJob, setAutopilotJob] = useState<JobRow | null>(null);

  // Chat focus — if the agent has signaled it's looking at a job, scroll the
  // page to it and highlight it briefly. The store is set by `set_chat_focus`.
  const chatFocus = useChatState();
  const focusedJobId = chatFocus.entity === "job" ? chatFocus.id : null;
  useEffect(() => {
    if (!focusedJobId) return;
    // Defer to next tick so React has painted the cards.
    const t = setTimeout(() => {
      const el = document.querySelector(`[data-job-id="${focusedJobId}"]`);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
    return () => clearTimeout(t);
  }, [focusedJobId]);

  // Agent-initiated autopilot — `propose_autopilot_run` confirms, drops the
  // job_id into the page-context channel (P2.C) and navigates here. Once the
  // jobs are loaded we open the AutopilotRunner with the right job.
  const jobsData = query.data;
  const pageCtx = usePageContext<{ job_id?: string; filter?: string }>("/jobs");
  const launchedAutopilotRef = useRef<string | null>(null);
  useEffect(() => {
    if (!jobsData || !pageCtx?.job_id) return;
    if (launchedAutopilotRef.current === pageCtx.job_id) return;
    const job = jobsData.find((j) => j.id === pageCtx.job_id);
    if (job) {
      launchedAutopilotRef.current = pageCtx.job_id;
      setAutopilotJob(job);
    }
  }, [jobsData, pageCtx]);

  // Agent-settable board filter (P2.E `filter_jobs`) — narrows the kanban /
  // list by title, company or notes. Always visibly indicated + clearable.
  const [agentFilter, setAgentFilter] = useState("");
  useEffect(() => {
    if (typeof pageCtx?.filter === "string") setAgentFilter(pageCtx.filter);
  }, [pageCtx]);
  const [draft, setDraft] = useState({
    title: "",
    company_name: "",
    url: "",
    description_raw: "",
  });

  const computeScore = useMutation({
    mutationFn: (id: string) => jobs.computeScore(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.jobs.all }),
    onError: (e: unknown) => toast.error("No pudimos calcular el match", (e as Error).message),
  });

  const create = useMutation({
    mutationFn: () => jobs.create({ ...draft, status: "interested" }),
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: queryKeys.jobs.all });
      setCreating(false);
      setDraft({ title: "", company_name: "", url: "", description_raw: "" });
      toast.success("Oferta añadida");
      if (created?.id && (created.description_raw ?? "").length > 30) {
        computeScore.mutate(created.id);
      }
    },
    onError: (e: unknown) => toast.error("No pudimos añadir", (e as Error).message),
  });

  const patch = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Parameters<typeof jobs.patch>[1] }) =>
      jobs.patch(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.jobs.all }),
    onError: (e: unknown) =>
      toast.error("No se pudo actualizar la candidatura", (e as Error).message),
  });

  const reorder = useMutation({
    mutationFn: (items: Parameters<typeof jobs.reorder>[0]) => jobs.reorder(items),
    onMutate: async (items) => {
      await qc.cancelQueries({ queryKey: queryKeys.jobs.all });
      const previous = qc.getQueryData<JobRow[]>(queryKeys.jobs.all);
      if (previous) {
        const byId = new Map(items.map((i) => [i.id, i]));
        const next = previous.map((j) => {
          const upd = byId.get(j.id);
          if (!upd) return j;
          return {
            ...j,
            position: upd.position,
            status: upd.status ?? j.status,
          };
        });
        // Sort: positioned items first by asc position, others fallback to created_at desc.
        next.sort((a, b) => {
          const ap = a.position;
          const bp = b.position;
          if (ap != null && bp != null) return ap - bp;
          if (ap != null) return -1;
          if (bp != null) return 1;
          return (b.created_at ?? "").localeCompare(a.created_at ?? "");
        });
        qc.setQueryData(queryKeys.jobs.all, next);
      }
      return { previous };
    },
    onError: (e: unknown, _vars, ctx) => {
      if (ctx?.previous) qc.setQueryData(queryKeys.jobs.all, ctx.previous);
      toast.error("No pudimos reordenar", (e as Error).message);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: queryKeys.jobs.all }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => jobs.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.jobs.all }),
    onError: (e: unknown) =>
      toast.error("No se pudo eliminar la candidatura", (e as Error).message),
  });

  const { pulling, progress } = usePullToRefresh(() => {
    qc.invalidateQueries({ queryKey: queryKeys.jobs.all });
  });

  const visibleItems = useMemo(() => {
    const all = query.data ?? [];
    const q = agentFilter.trim().toLowerCase();
    if (!q) return all;
    return all.filter(
      (j) =>
        (j.title ?? "").toLowerCase().includes(q) ||
        (j.company_name ?? "").toLowerCase().includes(q) ||
        (j.notes ?? "").toLowerCase().includes(q),
    );
  }, [query.data, agentFilter]);

  const grouped = useMemo(() => {
    const map: Record<JobStatus, JobRow[]> = {
      interested: [],
      applied: [],
      interviewing: [],
      offer: [],
      rejected: [],
      archived: [],
    };
    for (const j of visibleItems) {
      map[j.status]?.push(j);
    }
    return map;
  }, [visibleItems]);

  if (query.isLoading) return <PageSkeleton />;

  // Emptiness is judged on the UNFILTERED list so an agent filter never
  // flips the board into the first-run empty state.
  const items = query.data ?? [];
  const isEmpty = items.length === 0 && !creating;

  /** Single entry point for all drop events (inter- and intra-column).
   *  `anchor` is the position within the target column:
   *   - null            → drop at the bottom (e.g. dropped on column padding)
   *   - {id, side:top}  → drop above the card with that id
   *   - {id, side:bot}  → drop below the card with that id
   */
  const onDrop = (
    jobId: string,
    targetStatus: JobStatus,
    anchor: DropAnchor,
  ) => {
    const all = query.data ?? [];
    const dragged = all.find((j) => j.id === jobId);
    if (!dragged) return;

    // Column items *without* the dragged one — that's the array we insert into.
    const colItems = (grouped[targetStatus] ?? []).filter((j) => j.id !== jobId);
    let dropIndex = colItems.length;
    if (anchor) {
      const idx = colItems.findIndex((j) => j.id === anchor.id);
      if (idx >= 0) dropIndex = anchor.side === "top" ? idx : idx + 1;
    }
    const newPosition = computePosition(colItems, dropIndex);

    if (
      dragged.status === targetStatus &&
      dragged.position === newPosition
    ) {
      return;
    }

    reorder.mutate([
      {
        id: jobId,
        position: newPosition,
        ...(dragged.status !== targetStatus ? { status: targetStatus } : {}),
      },
    ]);
  };

  return (
    <Surface width="xl" spacing="md">
      {pulling && (
        <div className="fixed top-0 inset-x-0 z-50 flex justify-center pointer-events-none">
          <div
            className="bg-canvas border border-hairline shadow-soft rounded-full p-2 mt-2"
            style={{ transform: `translateY(${Math.min(progress * 40, 40)}px)` }}
          >
            <RefreshCw
              size={16}
              className={progress >= 1 ? "animate-spin text-leaf" : "text-stone"}
            />
          </div>
        </div>
      )}
      <PageHeader
        eyebrow="Búsqueda"
        title="Ofertas que vas siguiendo"
        subtitle="Tu pipeline. Cambia el estado a medida que avanzan, escribe notas, y desde cada oferta puedes generar un CV o carta adaptados."
        actions={
          <>
            <div
              role="tablist"
              aria-label="Vista"
              className="inline-flex items-center gap-0.5 rounded-tag bg-surface p-1 text-xs font-medium"
            >
              <ViewTab active={view === "kanban"} onClick={() => setView("kanban")}>
                Kanban
              </ViewTab>
              <ViewTab active={view === "list"} onClick={() => setView("list")}>
                Lista
              </ViewTab>
            </div>
            <Button
              variant="cta"
              onClick={() => setCreating(true)}
              leadingIcon={<Plus size={14} />}
            >
              Añadir oferta
            </Button>
          </>
        }
      />

      {/* P2.E — the agent can SEE the board and act on it in place. */}
      <AgentPageBridge
        pageId="jobs"
        readable={{
          description:
            "The jobs kanban board the user is viewing: view mode, active filter, totals and per-column jobs (id, title, company). Use `move_job_stage` to move a job between columns and `filter_jobs` to narrow the board.",
          value: {
            view,
            filter: agentFilter || null,
            total: items.length,
            visible: visibleItems.length,
            columns: COLUMNS.map((c) => ({
              id: c.id,
              label: c.label,
              count: grouped[c.id]?.length ?? 0,
              jobs: (grouped[c.id] ?? []).slice(0, 8).map((j) => ({
                id: j.id,
                title: j.title,
                company: j.company_name,
                match_score: j.match_score,
              })),
            })),
          },
        }}
        actions={[
          {
            name: "move_job_stage",
            description:
              "Move a job on the kanban the user is viewing to a new status. `new_status` must be one of: interested, applied, interviewing, offer, rejected, archived.",
            parameters: [
              { name: "job_id", type: "string", required: true },
              { name: "new_status", type: "string", required: true },
            ],
            handler: async (args) => {
              const jobId = String(args.job_id ?? "");
              const newStatus = String(args.new_status ?? "") as JobStatus;
              const valid: JobStatus[] = [
                "interested",
                "applied",
                "interviewing",
                "offer",
                "rejected",
                "archived",
              ];
              if (!valid.includes(newStatus)) {
                return `error: estado inválido '${newStatus}'. Válidos: ${valid.join(", ")}.`;
              }
              const job = (query.data ?? []).find((j) => j.id === jobId);
              if (!job) return `error: no encuentro la oferta '${jobId}' en el tablero.`;
              try {
                await patch.mutateAsync({ id: jobId, body: { status: newStatus } });
                return `ok: '${job.title ?? jobId}' movida a ${newStatus}.`;
              } catch (e) {
                return `error: ${(e as Error).message}`;
              }
            },
          },
          {
            name: "filter_jobs",
            description:
              "Filter the visible jobs board by free text (matches title, company and notes). Pass an empty string to clear the filter.",
            parameters: [{ name: "query", type: "string", required: true }],
            handler: (args) => {
              const q = String(args.query ?? "").trim();
              setAgentFilter(q);
              if (!q) return "ok: filtro retirado, tablero completo visible.";
              const matches = (query.data ?? []).filter(
                (j) =>
                  (j.title ?? "").toLowerCase().includes(q.toLowerCase()) ||
                  (j.company_name ?? "").toLowerCase().includes(q.toLowerCase()) ||
                  (j.notes ?? "").toLowerCase().includes(q.toLowerCase()),
              ).length;
              return `ok: filtro '${q}' aplicado — ${matches} oferta(s) visibles.`;
            },
          },
        ]}
      />

      {/* Agent-applied filter is never silent: visible chip + one-tap clear. */}
      {agentFilter && (
        <div className="flex items-center gap-2">
          <Badge tone="nova" size="sm" dot>
            Filtro: {agentFilter}
          </Badge>
          <button
            type="button"
            onClick={() => setAgentFilter("")}
            className="text-xs text-stone hover:text-ink transition-colors underline-offset-2 hover:underline"
          >
            Quitar filtro
          </button>
        </div>
      )}

      <AnimatePresence>
        {creating && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
          >
            <Card padding="lg">
              <h2 className="text-heading-sm font-medium tracking-tight mb-4">
                Nueva oferta
              </h2>
              <div className="grid md:grid-cols-2 gap-4">
                <Field label="Puesto">
                  {(p) => (
                    <Input
                      {...p}
                      value={draft.title}
                      onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                      placeholder="Senior Backend Engineer"
                    />
                  )}
                </Field>
                <Field label="Empresa">
                  {(p) => (
                    <Input
                      {...p}
                      value={draft.company_name}
                      onChange={(e) =>
                        setDraft({ ...draft, company_name: e.target.value })
                      }
                      placeholder="Acme Corp"
                    />
                  )}
                </Field>
                <Field label="URL" className="md:col-span-2">
                  {(p) => (
                    <Input
                      {...p}
                      value={draft.url}
                      onChange={(e) => setDraft({ ...draft, url: e.target.value })}
                      placeholder="https://…"
                    />
                  )}
                </Field>
                <Field label="Descripción (opcional)" className="md:col-span-2">
                  {(p) => (
                    <Textarea
                      {...p}
                      rows={5}
                      value={draft.description_raw}
                      onChange={(e) =>
                        setDraft({ ...draft, description_raw: e.target.value })
                      }
                      placeholder="Pega aquí la descripción. Te servirá luego para generar CV/carta."
                    />
                  )}
                </Field>
              </div>
              <div className="flex justify-end gap-2 mt-5">
                <Button variant="ghost" onClick={() => setCreating(false)}>
                  Cancelar
                </Button>
                <Button
                  onClick={() => create.mutate()}
                  loading={create.isPending}
                  disabled={!draft.title && !draft.url && !draft.description_raw}
                  leadingIcon={<Plus size={14} />}
                >
                  Añadir
                </Button>
              </div>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {isEmpty && (
        <Reveal>
          <Card padding="lg" tone="glass" className="text-center space-y-3">
            <Briefcase size={32} className="mx-auto text-stone" />
            <h3 className="text-heading-sm font-medium tracking-tight">
              Aún no estás siguiendo ninguna oferta
            </h3>
            <p className="text-sm text-stone max-w-md mx-auto">
              Cada oferta a la que apliques aparece aquí. Cuando generes un CV
              desde una oferta también queda registrada automáticamente.
            </p>
            <div className="pt-2">
              <Button
                variant="cta"
                onClick={() => setCreating(true)}
                leadingIcon={<Plus size={14} />}
              >
                Añadir tu primera oferta
              </Button>
            </div>
          </Card>
        </Reveal>
      )}

      {!isEmpty && view === "kanban" && (
        <div className="grid md:grid-cols-5 gap-3 md:gap-4">
          {COLUMNS.map((col) => (
            <KanbanColumn
              key={col.id}
              col={col}
              items={grouped[col.id] ?? []}
              onDrop={onDrop}
              onChangeStatus={(id, st) => patch.mutate({ id, body: { status: st } })}
              onDelete={(id) => remove.mutate(id)}
              onAutopilot={(job) => setAutopilotJob(job)}
              onRecomputeScore={(id) => computeScore.mutate(id)}
              onSetNextAction={(id, date) =>
                patch.mutate({ id, body: { next_action_at: date } })
              }
              recomputingId={computeScore.isPending ? computeScore.variables ?? null : null}
              focusedJobId={focusedJobId}
            />
          ))}
        </div>
      )}

      {!isEmpty && view === "list" && (
        <Stagger className="flex flex-col gap-3" delayStep={0.03}>
          {visibleItems.map((j) => (
            <JobListRow
              key={j.id}
              job={j}
              onChangeStatus={(st) => patch.mutate({ id: j.id, body: { status: st } })}
              onDelete={() => remove.mutate(j.id)}
              onAutopilot={() => setAutopilotJob(j)}
              onRecomputeScore={() => computeScore.mutate(j.id)}
              recomputing={computeScore.isPending && computeScore.variables === j.id}
            />
          ))}
        </Stagger>
      )}

      {autopilotJob && (
        <AutopilotRunner
          job={autopilotJob}
          onClose={() => setAutopilotJob(null)}
          onComplete={() => qc.invalidateQueries({ queryKey: queryKeys.jobs.all })}
        />
      )}
    </Surface>
  );
}

