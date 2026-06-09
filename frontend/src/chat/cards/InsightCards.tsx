/**
 * Generative INSIGHT cards — rich, display-only React the agent renders from a
 * tool call (TrajectoryCard / ExperienceCard / ProjectCard / SkillGapCard).
 *
 * These are the "show me my trajectory / experience / projects" surfaces: the
 * agent gathers data with a read tool, then calls present_trajectory /
 * present_experience_card / present_project_card / present_skill_gap with the
 * payload. Each card:
 *   • tolerates Partial args while status==='inProgress' (skeleton → fill),
 *   • is built on CSS-var tokens (typeTones/ProgressRing) → light/dark safe,
 *   • carries the entity ids it describes + a "Revélalo en el grafo" button that
 *     lights up those nodes (animate_graph highlightSet) — card and constellation
 *     are one thing.
 */
import { motion } from "motion/react";
import { Sparkles, Briefcase, FolderGit2, Target, GitBranch, ArrowUpRight } from "lucide-react";
import { Badge, ChatMessageMotion } from "@/ui";
import { ProgressRing } from "@/ui/ProgressRing";
import { useGraphLensState } from "@/graph/lensState";

const str = (v: unknown): string | undefined =>
  typeof v === "string" && v.trim() ? v.trim() : undefined;
const arr = (v: unknown): string[] =>
  Array.isArray(v) ? (v.filter((x) => typeof x === "string" && x.trim()) as string[]) : [];

/** Light up a set of nodes in the constellation (the card↔graph loop). */
function RevealInGraph({ ids, focus }: { ids: string[]; focus?: string }) {
  const clean = ids.filter(Boolean);
  if (clean.length === 0 && !focus) return null;
  return (
    <button
      type="button"
      onClick={() => {
        const s = useGraphLensState.getState();
        if (focus) s.setView({ focusEntityId: focus, mode: "focus" });
        if (clean.length) s.animate({ type: "highlightSet", ids: clean });
        else if (focus) s.animate({ type: "flyTo", entityId: focus });
      }}
      className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-hairline bg-canvas/60 px-2.5 py-1 text-[11px] text-ink/80 transition-colors hover:bg-canvas hover:text-ink"
    >
      <Sparkles size={12} />
      Revélalo en el grafo
    </button>
  );
}

function Shell({
  icon,
  badge,
  title,
  children,
}: {
  icon: React.ReactNode;
  badge: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <ChatMessageMotion>
      <div className="my-3 max-w-xl rounded-card border border-ink/[0.06] bg-surface p-5 shadow-soft">
        <div className="mb-3 flex items-start gap-3">
          <span aria-hidden className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-canvas text-ink">
            {icon}
          </span>
          <div className="min-w-0 space-y-1">
            <Badge tone="nova" size="sm">{badge}</Badge>
            <h4 className="text-base font-medium leading-tight text-ink">{title}</h4>
          </div>
        </div>
        {children}
      </div>
    </ChatMessageMotion>
  );
}

const reveal = (i: number) => ({
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.22, delay: Math.min(i * 0.05, 0.4), ease: [0.2, 0.8, 0.2, 1] as const },
});

// --- Trajectory ----------------------------------------------------------
export interface TrajectoryArgs {
  title?: string;
  narrative?: string;
  milestones?: Array<{ period?: string; title?: string; org?: string; detail?: string; entity_id?: string }>;
}
export function TrajectoryCard({ args, status }: { args: TrajectoryArgs; status?: string }) {
  const ms = Array.isArray(args.milestones) ? args.milestones : [];
  const ids = ms.map((m) => m?.entity_id).filter((x): x is string => !!x);
  const loading = status === "inProgress" && ms.length === 0;
  return (
    <Shell icon={<GitBranch size={18} />} badge="Trayectoria" title={str(args.title) || "Tu trayectoria"}>
      {str(args.narrative) && <p className="mb-3 text-sm leading-relaxed text-stone">{args.narrative}</p>}
      <ol className="relative ml-1 space-y-3 border-l border-hairline pl-4">
        {loading
          ? [0, 1, 2].map((i) => <li key={i} className="h-9 animate-pulse rounded bg-field" />)
          : ms.map((m, i) => (
              <motion.li key={i} {...reveal(i)} className="relative">
                <span aria-hidden className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-leaf ring-2 ring-surface" />
                <div className="flex items-baseline gap-2">
                  {str(m.period) && <span className="text-[11px] tabular-nums text-stone">{m.period}</span>}
                  <span className="text-sm font-medium text-ink">{str(m.title) || "—"}</span>
                </div>
                {str(m.org) && <div className="text-xs text-stone">{m.org}</div>}
                {str(m.detail) && <div className="mt-0.5 text-xs leading-snug text-stone/90">{m.detail}</div>}
              </motion.li>
            ))}
      </ol>
      <RevealInGraph ids={ids} />
    </Shell>
  );
}

// --- Experience ----------------------------------------------------------
export interface ExperienceArgs {
  entity_id?: string;
  role?: string;
  organization?: string;
  period?: string;
  impact?: string;
  highlights?: string[];
  skills?: string[];
  narrative?: string;
}
export function ExperienceCard({ args }: { args: ExperienceArgs; status?: string }) {
  const highlights = arr(args.highlights);
  const skills = arr(args.skills);
  const title = [str(args.role), str(args.organization)].filter(Boolean).join(" · ") || "Experiencia";
  return (
    <Shell icon={<Briefcase size={18} />} badge="Experiencia" title={title}>
      {str(args.period) && <div className="-mt-1 mb-2 text-[11px] tabular-nums text-stone">{args.period}</div>}
      {str(args.narrative) && <p className="mb-2 text-sm leading-relaxed text-stone">{args.narrative}</p>}
      {str(args.impact) && (
        <p className="mb-2 rounded-card bg-leaf-soft/60 px-3 py-1.5 text-sm text-ink">⟶ {args.impact}</p>
      )}
      {highlights.length > 0 && (
        <ul className="mb-2 space-y-1">
          {highlights.map((h, i) => (
            <motion.li key={i} {...reveal(i)} className="flex gap-2 text-sm text-ink/90">
              <span aria-hidden className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-stone" />
              {h}
            </motion.li>
          ))}
        </ul>
      )}
      {skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {skills.map((s) => <Badge key={s} tone="leaf" size="sm">{s}</Badge>)}
        </div>
      )}
      <RevealInGraph ids={args.entity_id ? [args.entity_id] : []} focus={str(args.entity_id)} />
    </Shell>
  );
}

// --- Project -------------------------------------------------------------
export interface ProjectArgs {
  entity_id?: string;
  name?: string;
  summary?: string;
  tech_stack?: string[];
  highlights?: string[];
  impact?: string;
  url?: string;
}
export function ProjectCard({ args }: { args: ProjectArgs; status?: string }) {
  const tech = arr(args.tech_stack);
  const highlights = arr(args.highlights);
  return (
    <Shell icon={<FolderGit2 size={18} />} badge="Proyecto" title={str(args.name) || "Proyecto"}>
      {str(args.summary) && <p className="mb-2 text-sm leading-relaxed text-stone">{args.summary}</p>}
      {str(args.impact) && (
        <p className="mb-2 rounded-card bg-leaf-soft/60 px-3 py-1.5 text-sm text-ink">⟶ {args.impact}</p>
      )}
      {highlights.length > 0 && (
        <ul className="mb-2 space-y-1">
          {highlights.map((h, i) => (
            <motion.li key={i} {...reveal(i)} className="flex gap-2 text-sm text-ink/90">
              <span aria-hidden className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-stone" />
              {h}
            </motion.li>
          ))}
        </ul>
      )}
      {tech.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tech.map((t) => <Badge key={t} tone="sunbeam" size="sm">{t}</Badge>)}
        </div>
      )}
      {str(args.url) && (
        <a href={args.url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs text-ink/80 underline-offset-2 hover:underline">
          Ver proyecto <ArrowUpRight size={12} />
        </a>
      )}
      <RevealInGraph ids={args.entity_id ? [args.entity_id] : []} focus={str(args.entity_id)} />
    </Shell>
  );
}

// --- Skill gap -----------------------------------------------------------
export interface SkillGapArgs {
  target_role?: string;
  match_score?: number;
  have?: string[];
  partial?: string[];
  missing?: string[];
  entity_ids?: string[];
  narrative?: string;
}
export function SkillGapCard({ args }: { args: SkillGapArgs; status?: string }) {
  const have = arr(args.have);
  const partial = arr(args.partial);
  const missing = arr(args.missing);
  const score = typeof args.match_score === "number" ? Math.max(0, Math.min(100, args.match_score)) : null;
  return (
    <Shell icon={<Target size={18} />} badge="Encaje de rol" title={str(args.target_role) || "Tu encaje"}>
      <div className="flex items-start gap-4">
        {score !== null && (
          <ProgressRing value={score} size={64} ariaLabel={`${Math.round(score)}% de encaje`}>
            <span className="text-sm font-semibold tabular-nums text-ink">{Math.round(score)}%</span>
          </ProgressRing>
        )}
        <div className="min-w-0 flex-1 space-y-2">
          {str(args.narrative) && <p className="text-sm leading-relaxed text-stone">{args.narrative}</p>}
          {have.length > 0 && (
            <div>
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-stone">Ya lo tienes</div>
              <div className="flex flex-wrap gap-1.5">{have.map((s) => <Badge key={s} tone="leaf" size="sm">{s}</Badge>)}</div>
            </div>
          )}
          {partial.length > 0 && (
            <div>
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-stone">En progreso</div>
              <div className="flex flex-wrap gap-1.5">{partial.map((s) => <Badge key={s} tone="sunbeam" size="sm">{s}</Badge>)}</div>
            </div>
          )}
          {missing.length > 0 && (
            <div>
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-stone">Te falta</div>
              <div className="flex flex-wrap gap-1.5">{missing.map((s) => <Badge key={s} tone="danger" size="sm">{s}</Badge>)}</div>
            </div>
          )}
        </div>
      </div>
      <RevealInGraph ids={arr(args.entity_ids)} />
    </Shell>
  );
}
