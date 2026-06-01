/**
 * UniverseProgress — the single "state of your universe" widget for the
 * universe sidebar.
 *
 * Merges the two former overlapping widgets (DiscoveryProgress card +
 * ProfileCompleteness) — both rendered a 0-100 ring + counts + gaps. One
 * header (ProgressRing + non-wrapping title) stays compact; the detail
 * (growth feed + completion checklist) is collapsed by default and expands on
 * demand, so it no longer dominates the sidebar or pushes the filters below the
 * fold. Keeps both data sources (useDiscoveryProgress + universe.summary +
 * preferences).
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "motion/react";
import {
  ArrowRight,
  Briefcase,
  GraduationCap,
  Sparkles,
  Languages,
  MessageSquare,
  Heart,
  ChevronDown,
} from "lucide-react";
import { universe } from "@/shared/api";
import { queryKeys } from "@/shared/queryKeys";
import { useDiscoveryProgress } from "@/shared/hooks/useDiscoveryProgress";
import { KIND_LABELS } from "@/shared/kindColors";
import { Badge, Card, ProgressRing, cn } from "@/ui";

interface Check {
  id: string;
  label: string;
  done: boolean;
  Icon: typeof Briefcase;
  cta?: { label: string; href: string };
}

const SOURCE_LABELS: Record<string, string> = {
  agent_chat: "Chat",
  import: "Import",
  manual: "Manual",
  onboarding: "Onboarding",
};

export function UniverseProgress() {
  const [open, setOpen] = useState(false);
  const summary = useQuery({
    queryKey: queryKeys.universe.summary,
    queryFn: () => universe.summary(),
  });
  const prefs = useQuery({
    queryKey: queryKeys.preferences.all,
    queryFn: () => universe.preferences.get(),
    retry: false,
  });
  const discovery = useDiscoveryProgress();

  if (summary.isLoading || !summary.data) return null;

  const counts = summary.data.counts;
  const hasPrefs = !!(
    prefs.data &&
    (prefs.data.status || (prefs.data.preferred_roles?.length ?? 0) > 0)
  );

  const checks: Check[] = [
    { id: "headline", label: "Tu titular", done: !!summary.data.headline, Icon: Sparkles, cta: { label: "Definir", href: "#/" } },
    { id: "summary", label: "Resumen profesional", done: !!summary.data.summary, Icon: MessageSquare, cta: { label: "Añadir desde chat", href: "#/" } },
    { id: "experiences", label: `Experiencias (${counts.experiences})`, done: counts.experiences >= 1, Icon: Briefcase, cta: { label: "Importar", href: "#/connections" } },
    { id: "educations", label: `Educación (${counts.educations})`, done: counts.educations >= 1, Icon: GraduationCap, cta: { label: "Añadir", href: "#/universe" } },
    { id: "skills", label: `Skills (${counts.skills})`, done: counts.skills >= 5, Icon: Sparkles, cta: { label: "Añadir 5+", href: "#/" } },
    { id: "languages", label: `Idiomas (${counts.languages})`, done: counts.languages >= 1, Icon: Languages, cta: { label: "Añadir", href: "#/universe" } },
    { id: "preferences", label: "Preferencias de carrera", done: hasPrefs, Icon: Heart, cta: { label: "Definir", href: "#/preferences" } },
  ];

  const doneCount = checks.filter((c) => c.done).length;
  const score = Math.round((doneCount / checks.length) * 100);
  const missing = checks.filter((c) => !c.done);
  const isComplete = missing.length === 0;

  const d = discovery.data;
  const isAlive = !!d?.is_alive;
  const totalEntities = d?.total_entities ?? 0;
  const recent = d?.recent_discoveries ?? [];
  const sparse = d?.sparse_dimensions ?? [];

  return (
    <Card padding="sm" className="relative overflow-hidden border border-hairline">
      <div
        aria-hidden
        className="absolute -top-16 -right-12 h-40 w-40 rounded-full bg-leaf/10 blur-3xl pointer-events-none"
      />
      <div className="relative">
        {/* Header — ring + non-wrapping title + alive pill + collapse toggle */}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex w-full items-center gap-3 text-left"
        >
          <ProgressRing value={score} size={44} ariaLabel={`Universo ${score}% completo`}>
            <span className="text-[13px] font-medium tabular-nums text-ink">{score}</span>
          </ProgressRing>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <h3 className="truncate font-display text-heading-sm leading-tight text-ink">
                Universo {isComplete ? "completo" : "en marcha"}
              </h3>
              {isAlive && (
                <span className="relative flex h-1.5 w-1.5 shrink-0" title="Universo activo">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-leaf opacity-75" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-leaf" />
                </span>
              )}
            </div>
            <p className="mt-0.5 truncate text-xs text-stone">
              {isComplete ? "Listo para generar CV" : `${doneCount}/${checks.length} pasos`}
              {totalEntities > 0 ? ` · ${totalEntities} entidades` : ""}
            </p>
          </div>
          <ChevronDown
            size={16}
            className={cn("shrink-0 text-stone transition-transform duration-180", open && "rotate-180")}
          />
        </button>

        {/* Top gap nudge — always visible when collapsed + incomplete */}
        {!open && !isComplete && missing[0] && (
          <div className="mt-3">
            <CompletenessRow check={missing[0]} />
          </div>
        )}

        <AnimatePresence initial={false}>
          {open && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
              className="overflow-hidden"
            >
              <div className="space-y-4 pt-4">
                {/* Completar — the checklist */}
                {!isComplete && (
                  <div className="space-y-2">
                    <span className="eyebrow">Completar</span>
                    <div className="grid grid-cols-1 gap-2">
                      {missing.map((c) => (
                        <CompletenessRow key={c.id} check={c} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Crecimiento — discovery feed + gaps */}
                {(recent.length > 0 || sparse.length > 0) && (
                  <div className="space-y-2">
                    <span className="eyebrow">Crecimiento</span>
                    {recent.length > 0 && (
                      <div className="space-y-1" aria-live="polite">
                        {recent.slice(0, 3).map((r, i) => (
                          <div key={i} className="flex items-center gap-2 text-xs">
                            <span aria-hidden className="h-1.5 w-1.5 shrink-0 rounded-full bg-nova" />
                            <span className="capitalize text-ink">
                              {KIND_LABELS[r.entity_type] || r.entity_type}
                            </span>
                            <span className="text-stone">{SOURCE_LABELS[r.source] || r.source}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    {sparse.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {sparse.map((dim) => (
                          <Badge key={dim} tone="stone" size="sm">
                            {KIND_LABELS[dim] || dim}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Card>
  );
}

function CompletenessRow({ check }: { check: Check }) {
  const { Icon, cta, label } = check;
  return (
    <a
      href={cta?.href ?? "#/"}
      className="group flex items-center gap-2.5 rounded-card border border-ink/[0.06] bg-canvas p-3 transition-colors duration-180 hover:border-ink/15"
    >
      <span
        aria-hidden
        className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface text-stone transition-colors group-hover:text-ink"
      >
        <Icon size={12} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm text-ink">{label}</div>
      </div>
      <span className="inline-flex shrink-0 items-center gap-0.5 whitespace-nowrap text-xs text-stone transition-colors group-hover:text-ink">
        {cta?.label ?? "Añadir"}
        <ArrowRight size={10} className="shrink-0" />
      </span>
    </a>
  );
}
