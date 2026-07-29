/** Presentational parts of the jobs board.
 *
 * Split out of JobsPage.tsx, which was 1161 lines: the page component plus
 * seven components used only by it. None of these is referenced anywhere else,
 * so this is a pure move.
 */
import { useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  Archive, CalendarClock, ChevronDown, ExternalLink, Loader2,
  RefreshCw, Trash2, Wand2,
} from "lucide-react";

import { useChatState } from "@/chat/state";
import { type JobRow, type JobStatus } from "@/shared/api";
import { Badge, Button, Card, Popover, cn } from "@/ui";

import { ARCHIVED_TONE, COLUMNS, type ColumnDef, type DropAnchor } from "./columns";

export function ViewTab({
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

export function KanbanColumn({
  col,
  items,
  onDrop,
  onChangeStatus,
  onDelete,
  onAutopilot,
  onRecomputeScore,
  onSetNextAction,
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
  onSetNextAction: (id: string, date: string) => void;
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
              onSetNextAction={(date) => onSetNextAction(j.id, date)}
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

export function KanbanCard({
  job,
  targetStatus,
  onDrop,
  onChangeStatus,
  onDelete,
  onAutopilot,
  onRecomputeScore,
  onSetNextAction,
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
  onSetNextAction: (date: string) => void;
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
      <label
        className="mt-2 flex items-center gap-1.5 text-[11px] text-stone"
        title="Fecha de seguimiento — crea un recordatorio"
        onClick={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
      >
        <CalendarClock size={12} className={cn(job.next_action_at && "text-nova")} />
        <input
          type="date"
          draggable={false}
          value={job.next_action_at ? job.next_action_at.slice(0, 10) : ""}
          onChange={(e) => onSetNextAction(e.target.value)}
          className="bg-transparent outline-none text-[11px] text-stone focus:text-ink"
          aria-label="Fecha de seguimiento"
        />
      </label>
      <div className="flex items-center gap-1.5 flex-wrap mt-2.5">
        {job.match_score != null ? (
          <Popover
            placement="bottom-start"
            trigger={
              <span
                title="Ver desglose del match"
                className="inline-flex items-center gap-1 cursor-pointer"
              >
                <Badge tone="nova" size="sm">
                  {recomputing ? "…" : `${job.match_score}% match`}
                </Badge>
                {recomputing && (
                  <Loader2 size={9} className="animate-spin text-stone" />
                )}
              </span>
            }
          >
            <MatchScorecard
              job={job}
              hasJD={hasJD}
              recomputing={recomputing}
              onRecompute={onRecomputeScore}
            />
          </Popover>
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
        <a
          href={`#/jobs/${job.id}/prep`}
          draggable={false}
          onClick={(e) => e.stopPropagation()}
          className="inline-flex items-center gap-0.5 text-xs text-stone hover:text-ink transition-colors"
          title="Preparar la entrevista para esta oferta"
        >
          <span>entrevista</span>
        </a>
        <button
          type="button"
          onClick={() => {
            // Hand the offer to /cv/new via the page-context channel (P2.C).
            useChatState.getState().setPendingPageContext({
              route: "/cv/new",
              context: {
                job_url: job.url ?? undefined,
                job_description: job.description_raw || undefined,
              },
            });
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

export function DimBar({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] text-stone w-20 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-ink/[0.08] overflow-hidden">
        <div
          className="h-full rounded-full bg-nova transition-[width] duration-300"
          style={{ width: `${value ?? 0}%` }}
        />
      </div>
      <span className="text-[11px] text-ink w-8 text-right tabular-nums">
        {value != null ? `${value}%` : "—"}
      </span>
    </div>
  );
}

export function MatchScorecard({
  job,
  hasJD,
  recomputing,
  onRecompute,
}: {
  job: JobRow;
  hasJD: boolean;
  recomputing: boolean;
  onRecompute: () => void;
}) {
  const m = job.match;
  return (
    <div
      className="w-64 p-3"
      onClick={(e) => e.stopPropagation()}
      role="presentation"
    >
      <div className="flex items-baseline justify-between mb-2.5">
        <span className="text-[11px] uppercase tracking-wider text-stone">
          Match con tu universo
        </span>
        <span className="font-display text-heading-sm text-ink leading-none">
          {job.match_score}%
        </span>
      </div>

      {m ? (
        <>
          <div className="space-y-1.5 mb-3">
            <DimBar label="Skills" value={m.dimensions.skills} />
            <DimBar label="Experiencia" value={m.dimensions.experience} />
            <DimBar label="Formación" value={m.dimensions.education} />
          </div>
          {m.keyword_coverage != null && (
            <p className="text-[11px] text-stone mb-2.5">
              Keywords ATS cubiertas:{" "}
              <span className="text-ink font-medium">{m.keyword_coverage}%</span>
            </p>
          )}
          {m.strengths.length > 0 && (
            <div className="mb-2">
              <p className="text-[11px] text-stone mb-1">Coincidencias</p>
              <div className="flex flex-wrap gap-1">
                {m.strengths.slice(0, 8).map((s) => (
                  <Badge key={s} tone="leaf" size="sm">
                    {s}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          {m.gaps.length > 0 && (
            <div className="mb-2.5">
              <p className="text-[11px] text-stone mb-1">Brechas a cubrir</p>
              <div className="flex flex-wrap gap-1">
                {m.gaps.slice(0, 8).map((g) => (
                  <Badge key={g} tone="amber" size="sm">
                    {g}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <p className="text-xs text-stone mb-3 leading-relaxed">
          Recalcula para ver el desglose por dimensión y las brechas de keywords
          frente a tu universo.
        </p>
      )}

      <Button
        size="sm"
        variant="outline"
        fullWidth
        onClick={onRecompute}
        loading={recomputing}
        disabled={recomputing || !hasJD}
        leadingIcon={<RefreshCw size={13} />}
        title={hasJD ? "Recalcular match" : "Sin descripción para recalcular"}
      >
        {recomputing ? "Recalculando" : "Recalcular match"}
      </Button>
    </div>
  );
}

export function JobListRow({
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

export function RowMenu({
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
                className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-danger-soft text-danger"
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
