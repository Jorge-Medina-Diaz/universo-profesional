import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useChatState } from "@/chat/state";
import { queryKeys } from "@/shared/queryKeys";
import { AnimatePresence, motion } from "motion/react";
import {
  Plus,
  ExternalLink,
  Trash2,
  Briefcase,
  ChevronDown,
  Send,
  Coffee,
  Trophy,
  XCircle,
  Heart,
  Archive,
  Wand2,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { jobs, type JobRow, type JobStatus } from "@/shared/api";
import { usePullToRefresh } from "@/shared/usePullToRefresh";
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
  cn,
  toast,
} from "@/ui";
import { AutopilotRunner } from "./_jobs/AutopilotRunner";

type ViewMode = "kanban" | "list";

interface ColumnDef {
  id: JobStatus;
  label: string;
  Icon: typeof Briefcase;
  tone: "leaf" | "sunbeam" | "stone" | "amber";
}

const COLUMNS: ColumnDef[] = [
  { id: "interested", label: "Interesado", Icon: Heart, tone: "stone" },
  { id: "applied", label: "Aplicado", Icon: Send, tone: "leaf" },
  { id: "interviewing", label: "Entrevistas", Icon: Coffee, tone: "sunbeam" },
  { id: "offer", label: "Oferta", Icon: Trophy, tone: "leaf" },
  { id: "rejected", label: "Rechazado", Icon: XCircle, tone: "amber" },
];

const ARCHIVED_TONE: Record<JobStatus, "leaf" | "sunbeam" | "stone" | "amber"> = {
  interested: "stone",
  applied: "leaf",
  interviewing: "sunbeam",
  offer: "leaf",
  rejected: "amber",
  archived: "stone",
};

type DropAnchor = { id: string; side: "top" | "bottom" } | null;

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

  // Agent-initiated autopilot — `propose_autopilot_run` confirms then drops
  // a job_id in sessionStorage and redirects here. We read it on mount and
  // open the AutopilotRunner with the right job.
  const jobsData = query.data;
  useEffect(() => {
    if (!jobsData) return;
    try {
      const raw = sessionStorage.getItem("cvs-saas-autopilot-launch");
      if (!raw) return;
      sessionStorage.removeItem("cvs-saas-autopilot-launch");
      const data = JSON.parse(raw) as { job_id?: string };
      if (!data.job_id) return;
      const job = jobsData.find((j) => j.id === data.job_id);
      if (job) setAutopilotJob(job);
    } catch {
      /* ignore */
    }
  }, [jobsData]);
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

  const grouped = useMemo(() => {
    const items = query.data ?? [];
    const map: Record<JobStatus, JobRow[]> = {
      interested: [],
      applied: [],
      interviewing: [],
      offer: [],
      rejected: [],
      archived: [],
    };
    for (const j of items) {
      map[j.status]?.push(j);
    }
    return map;
  }, [query.data]);

  if (query.isLoading) return <PageSkeleton />;

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
            <Button onClick={() => setCreating(true)} leadingIcon={<Plus size={14} />}>
              Añadir oferta
            </Button>
          </>
        }
      />

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
          <Card padding="lg" className="text-center space-y-3">
            <Briefcase size={32} className="mx-auto text-stone" />
            <h3 className="text-heading-sm font-medium tracking-tight">
              Aún no estás siguiendo ninguna oferta
            </h3>
            <p className="text-sm text-stone max-w-md mx-auto">
              Cada oferta a la que apliques aparece aquí. Cuando generes un CV
              desde una oferta también queda registrada automáticamente.
            </p>
            <div className="pt-2">
              <Button onClick={() => setCreating(true)} leadingIcon={<Plus size={14} />}>
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
              recomputingId={computeScore.isPending ? computeScore.variables ?? null : null}
              focusedJobId={focusedJobId}
            />
          ))}
        </div>
      )}

      {!isEmpty && view === "list" && (
        <Stagger className="flex flex-col gap-3" delayStep={0.03}>
          {items.map((j) => (
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

function ViewTab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        "rounded-tag px-3 py-1 transition-colors duration-180 ease-pirsch",
        active ? "bg-canvas text-ink shadow-soft" : "text-stone hover:text-ink",
      )}
    >
      {children}
    </button>
  );
}

function KanbanColumn({
  col,
  items,
  onDrop,
  onChangeStatus,
  onDelete,
  onAutopilot,
  onRecomputeScore,
  recomputingId,
  focusedJobId,
}: {
  col: ColumnDef;
  items: JobRow[];
  onDrop: (jobId: string, targetStatus: JobStatus, anchor: DropAnchor) => void;
  onChangeStatus: (id: string, st: JobStatus) => void;
  onDelete: (id: string) => void;
  onAutopilot: (job: JobRow) => void;
  onRecomputeScore: (id: string) => void;
  recomputingId: string | null;
  focusedJobId: string | null;
}) {
  const [hover, setHover] = useState(false);
  const dragCountRef = useRef(0);

  return (
    <section
      onDragOver={(e) => {
        if (e.dataTransfer.types.includes("application/x-cvs-job")) {
          e.preventDefault();
        }
      }}
      onDragEnter={(e) => {
        if (!e.dataTransfer.types.includes("application/x-cvs-job")) return;
        e.preventDefault();
        dragCountRef.current++;
        setHover(true);
      }}
      onDragLeave={() => {
        dragCountRef.current = Math.max(0, dragCountRef.current - 1);
        if (dragCountRef.current === 0) setHover(false);
      }}
      onDrop={(e) => {
        const id = e.dataTransfer.getData("application/x-cvs-job");
        dragCountRef.current = 0;
        setHover(false);
        // No specific card targeted → drop at end of column.
        if (id) onDrop(id, col.id, null);
      }}
      className={cn(
        "flex flex-col rounded-card bg-surface min-h-[200px] transition-colors duration-180 ease-pirsch",
        hover && "bg-leaf-soft/60 ring-2 ring-leaf",
      )}
    >
      <header className="flex items-center gap-2 px-3 py-3 border-b border-ink/5">
        <span
          aria-hidden
          className={cn(
            "inline-flex items-center justify-center w-7 h-7 rounded-full shrink-0",
            col.tone === "leaf" && "bg-leaf-soft text-leaf-ink",
            col.tone === "sunbeam" && "bg-sunbeam-soft text-sunbeam-ink",
            col.tone === "stone" && "bg-canvas text-stone",
            col.tone === "amber" && "bg-sunbeam-soft text-sunbeam-ink",
          )}
        >
          <col.Icon size={12} />
        </span>
        <h3 className="text-sm font-medium text-ink leading-none flex-1">{col.label}</h3>
        <Badge tone="stone" size="sm">
          {items.length}
        </Badge>
      </header>
      <div className="flex flex-col gap-2 p-2 flex-1">
        <AnimatePresence>
          {items.map((j) => (
            <KanbanCard
              key={j.id}
              job={j}
              targetStatus={col.id}
              onDrop={onDrop}
              onChangeStatus={(st) => onChangeStatus(j.id, st)}
              onDelete={() => onDelete(j.id)}
              onAutopilot={() => onAutopilot(j)}
              onRecomputeScore={() => onRecomputeScore(j.id)}
              recomputing={recomputingId === j.id}
              focused={focusedJobId === j.id}
            />
          ))}
        </AnimatePresence>
        {items.length === 0 && (
          <p className="text-xs text-stone text-center py-6">
            {hover ? "Suelta aquí" : "Vacío"}
          </p>
        )}
      </div>
    </section>
  );
}

type DropEdge = "top" | "bottom" | null;

function KanbanCard({
  job,
  targetStatus,
  onDrop,
  onChangeStatus,
  onDelete,
  onAutopilot,
  onRecomputeScore,
  recomputing,
  focused,
}: {
  job: JobRow;
  targetStatus: JobStatus;
  onDrop: (jobId: string, targetStatus: JobStatus, anchor: DropAnchor) => void;
  onChangeStatus: (st: JobStatus) => void;
  onDelete: () => void;
  onAutopilot: () => void;
  onRecomputeScore: () => void;
  recomputing: boolean;
  focused: boolean;
}) {
  const [edge, setEdge] = useState<DropEdge>(null);
  const hasJD = (job.description_raw ?? "").length > 30;

  return (
    <motion.article
      layout
      data-job-id={job.id}
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -10 }}
      transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
      draggable
      onDragStart={(e) => {
        const dt = (e as unknown as React.DragEvent<HTMLElement>).dataTransfer;
        dt.effectAllowed = "move";
        dt.setData("application/x-cvs-job", job.id);
      }}
      onDragOver={(ev) => {
        const e = ev as unknown as React.DragEvent<HTMLElement>;
        if (!e.dataTransfer.types.includes("application/x-cvs-job")) return;
        e.preventDefault();
        e.stopPropagation();
        const rect = e.currentTarget.getBoundingClientRect();
        const isTop = e.clientY - rect.top < rect.height / 2;
        setEdge(isTop ? "top" : "bottom");
      }}
      onDragLeave={() => setEdge(null)}
      onDrop={(ev) => {
        const e = ev as unknown as React.DragEvent<HTMLElement>;
        e.preventDefault();
        e.stopPropagation();
        const id = e.dataTransfer.getData("application/x-cvs-job");
        const dropSide = edge ?? "bottom";
        setEdge(null);
        if (!id || id === job.id) return;
        onDrop(id, targetStatus, { id: job.id, side: dropSide });
      }}
      className={cn(
        "group relative rounded-card bg-canvas p-3 border border-ink/[0.06] hover:border-ink/25 hover:shadow-soft transition-all duration-180 cursor-grab active:cursor-grabbing",
        edge === "top" && "ring-2 ring-leaf ring-offset-0",
        edge === "bottom" && "ring-2 ring-leaf ring-offset-0",
        focused &&
          "ring-2 ring-sunbeam ring-offset-2 ring-offset-surface shadow-soft",
      )}
    >
      {edge && (
        <div
          aria-hidden
          className={cn(
            "absolute left-2 right-2 h-[3px] rounded-full bg-leaf",
            edge === "top" ? "-top-1" : "-bottom-1",
          )}
        />
      )}
      <header className="flex items-start justify-between gap-2 mb-1.5">
        <h4 className="text-sm font-medium text-ink leading-tight line-clamp-2">
          {job.title || "Sin título"}
        </h4>
        <RowMenu
          status={job.status}
          onChangeStatus={onChangeStatus}
          onDelete={onDelete}
        />
      </header>
      {job.company_name && (
        <p className="text-xs text-stone truncate">{job.company_name}</p>
      )}
      <div className="flex items-center gap-1.5 flex-wrap mt-2.5">
        {job.match_score != null ? (
          <button
            type="button"
            onClick={onRecomputeScore}
            disabled={!hasJD || recomputing}
            title={hasJD ? "Recalcular match" : "Sin descripción para recalcular"}
            className="inline-flex items-center gap-1 disabled:cursor-not-allowed"
          >
            <Badge tone="leaf" size="sm">
              {recomputing ? "…" : `${job.match_score}% match`}
            </Badge>
            {hasJD && !recomputing && (
              <RefreshCw size={9} className="text-stone hover:text-ink" />
            )}
            {recomputing && <Loader2 size={9} className="animate-spin text-stone" />}
          </button>
        ) : (
          hasJD && (
            <button
              type="button"
              onClick={onRecomputeScore}
              disabled={recomputing}
              className="inline-flex items-center gap-1 text-xs text-stone hover:text-ink transition-colors disabled:opacity-60"
              title="Calcular match con tu universo"
            >
              {recomputing ? (
                <Loader2 size={10} className="animate-spin" />
              ) : (
                <RefreshCw size={10} />
              )}
              match
            </button>
          )
        )}
        {job.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-0.5 text-xs text-stone hover:text-ink transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink size={10} />
            <span>oferta</span>
          </a>
        )}
        <button
          type="button"
          onClick={() => {
            try {
              sessionStorage.setItem(
                "cvs-saas-prefill-job",
                JSON.stringify({
                  job_url: job.url,
                  job_description: job.description_raw,
                  title: job.title,
                  company_name: job.company_name,
                }),
              );
            } catch {
              /* ignore */
            }
            window.location.hash = "#/cv/new";
          }}
          className="inline-flex items-center gap-0.5 text-xs text-stone hover:text-ink transition-colors ml-auto"
        >
          <Wand2 size={10} />
          CV
        </button>
        <button
          type="button"
          onClick={onAutopilot}
          className="inline-flex items-center gap-0.5 text-xs font-medium text-ink bg-sunbeam hover:bg-[#ffcf45] px-1.5 py-0.5 rounded-md transition-colors"
          title="CV + carta + marcar aplicada"
        >
          <Wand2 size={10} />
          Auto
        </button>
      </div>
    </motion.article>
  );
}

function JobListRow({
  job,
  onChangeStatus,
  onDelete,
  onAutopilot,
  onRecomputeScore,
  recomputing,
}: {
  job: JobRow;
  onChangeStatus: (st: JobStatus) => void;
  onDelete: () => void;
  onAutopilot: () => void;
  onRecomputeScore: () => void;
  recomputing: boolean;
}) {
  const meta = COLUMNS.find((c) => c.id === job.status);
  const hasJD = (job.description_raw ?? "").length > 30;
  return (
    <Card padding="md" className="flex items-center gap-4 flex-wrap">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <h4 className="text-sm font-medium text-ink truncate">
            {job.title || "Sin título"}
          </h4>
          {meta && (
            <Badge tone={ARCHIVED_TONE[job.status]} size="sm" dot>
              {meta.label}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-stone mt-0.5">
          {job.company_name && <span>{job.company_name}</span>}
          {job.applied_at && <span>· aplicado {new Date(job.applied_at).toLocaleDateString()}</span>}
          {job.match_score != null && <span>· {job.match_score}% match</span>}
        </div>
      </div>
      {hasJD && (
        <Button
          size="sm"
          variant="ghost"
          onClick={onRecomputeScore}
          loading={recomputing}
          leadingIcon={<RefreshCw size={12} />}
        >
          Match
        </Button>
      )}
      <Button
        size="sm"
        variant="outline"
        onClick={onAutopilot}
        leadingIcon={<Wand2 size={12} />}
      >
        Autopilot
      </Button>
      <RowMenu
        status={job.status}
        onChangeStatus={onChangeStatus}
        onDelete={onDelete}
      />
    </Card>
  );
}

function RowMenu({
  status,
  onChangeStatus,
  onDelete,
}: {
  status: JobStatus;
  onChangeStatus: (st: JobStatus) => void;
  onDelete: () => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="inline-flex items-center gap-1 text-xs text-stone hover:text-ink transition-colors px-2 py-1 rounded-btn hover:bg-black/[0.04]"
      >
        Mover
        <ChevronDown size={10} />
      </button>
      <AnimatePresence>
        {open && (
          <>
            <button
              type="button"
              aria-label="Cerrar"
              onClick={() => setOpen(false)}
              className="fixed inset-0 z-30 cursor-default"
            />
            <motion.div
              role="menu"
              initial={{ opacity: 0, y: -4, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -4, scale: 0.97 }}
              transition={{ duration: 0.18 }}
              className="absolute right-0 top-full mt-1 z-40 w-44 rounded-card bg-canvas shadow-lift border border-ink/8 overflow-hidden text-xs"
            >
              {COLUMNS.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    onChangeStatus(c.id);
                    setOpen(false);
                  }}
                  disabled={c.id === status}
                  className={cn(
                    "w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-surface transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
                    c.id === status && "bg-surface text-ink",
                  )}
                >
                  <c.Icon size={12} />
                  {c.label}
                </button>
              ))}
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  onChangeStatus("archived");
                  setOpen(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-surface text-stone border-t border-ink/5"
              >
                <Archive size={12} /> Archivar
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  onDelete();
                  setOpen(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-red-50 text-red-600"
              >
                <Trash2 size={12} /> Eliminar
              </button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
