/**
 * Profile completeness card.
 *
 * Heuristic 0-100 score based on what the user has filled in. Visible on
 * the Universe page. Nudges to fill the gaps it detects — each missing
 * piece links to the right action (chat, preferences, connections, etc).
 */
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import {
  ArrowRight,
  Briefcase,
  GraduationCap,
  Sparkles,
  Languages,
  MessageSquare,
  Heart,
  CheckCircle2,
} from "lucide-react";
import { universe } from "@/shared/api";
import { queryKeys } from "@/shared/queryKeys";
import { Badge, Card, Reveal, cn } from "@/ui";

interface Check {
  id: string;
  label: string;
  done: boolean;
  Icon: typeof Briefcase;
  cta?: { label: string; href: string };
}

export function ProfileCompleteness() {
  const summary = useQuery({
    queryKey: queryKeys.universe.summary,
    queryFn: () => universe.summary(),
  });
  const prefs = useQuery({
    queryKey: queryKeys.preferences.all,
    queryFn: () => universe.preferences.get(),
    retry: false,
  });

  if (summary.isLoading) return null;
  if (!summary.data) return null;

  const counts = summary.data.counts;
  const hasHeadline = !!summary.data.headline;
  const hasSummary = !!summary.data.summary;
  const hasPrefs = !!(prefs.data && (prefs.data.status || (prefs.data.preferred_roles?.length ?? 0) > 0));

  const checks: Check[] = [
    {
      id: "headline",
      label: "Tu titular",
      done: hasHeadline,
      Icon: Sparkles,
      cta: { label: "Definir", href: "#/" },
    },
    {
      id: "summary",
      label: "Resumen profesional",
      done: hasSummary,
      Icon: MessageSquare,
      cta: { label: "Añadir desde chat", href: "#/" },
    },
    {
      id: "experiences",
      label: `Experiencias (${counts.experiences})`,
      done: counts.experiences >= 1,
      Icon: Briefcase,
      cta: { label: "Importar", href: "#/connections" },
    },
    {
      id: "educations",
      label: `Educación (${counts.educations})`,
      done: counts.educations >= 1,
      Icon: GraduationCap,
      cta: { label: "Añadir", href: "#/universe" },
    },
    {
      id: "skills",
      label: `Skills (${counts.skills})`,
      done: counts.skills >= 5,
      Icon: Sparkles,
      cta: { label: "Añadir 5+", href: "#/" },
    },
    {
      id: "languages",
      label: `Idiomas (${counts.languages})`,
      done: counts.languages >= 1,
      Icon: Languages,
      cta: { label: "Añadir", href: "#/universe" },
    },
    {
      id: "preferences",
      label: "Preferencias de carrera",
      done: hasPrefs,
      Icon: Heart,
      cta: { label: "Definir", href: "#/preferences" },
    },
  ];

  const doneCount = checks.filter((c) => c.done).length;
  const score = Math.round((doneCount / checks.length) * 100);
  const missing = checks.filter((c) => !c.done);
  const isComplete = doneCount === checks.length;

  return (
    <Reveal>
      <Card padding="lg" className="relative overflow-hidden">
        <div
          aria-hidden
          className="absolute -top-16 -right-12 w-48 h-48 rounded-full bg-leaf/15 blur-3xl pointer-events-none"
        />
        <div className="relative space-y-4">
          <div className="flex items-center gap-4">
            <CompletenessGauge score={score} />
            <div className="min-w-0 space-y-1.5">
              <h3 className="font-display text-[22px] leading-tight text-ink">
                Universo {isComplete ? "completo" : "en marcha"}
              </h3>
              {isComplete ? (
                <Badge tone="leaf" dot>
                  Listo para generar CV
                </Badge>
              ) : (
                <Badge tone="sunbeam" size="sm">
                  {doneCount} de {checks.length} pasos
                </Badge>
              )}
            </div>
          </div>
          <p className="text-sm text-stone leading-relaxed">
            {isComplete
              ? "Buen trabajo. Cualquier CV que generes ahora aprovecha al máximo tu universo."
              : `Cada hueco que rellenes mejora la calidad de tus CVs adaptados. Te quedan ${missing.length} pasos.`}
          </p>
          {!isComplete && missing.length > 0 && (
            <div className="grid grid-cols-1 gap-2">
              {missing.slice(0, 4).map((c) => (
                <CompletenessRow key={c.id} check={c} />
              ))}
            </div>
          )}
        </div>
      </Card>
    </Reveal>
  );
}

function CompletenessGauge({ score }: { score: number }) {
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const dash = (score / 100) * circumference;
  const tone =
    score >= 80
      ? "var(--color-leafy-green)"
      : score >= 50
        ? "var(--color-sunbeam-yellow)"
        : "var(--color-leafy-green)";
  return (
    <div className="relative shrink-0">
      <svg width="100" height="100" viewBox="0 0 100 100" aria-hidden>
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke="rgba(0,0,0,0.06)"
          strokeWidth="8"
        />
        <motion.circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={tone}
          strokeWidth="8"
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
          initial={{ strokeDasharray: `0 ${circumference}` }}
          animate={{ strokeDasharray: `${dash} ${circumference}` }}
          transition={{ duration: 1.1, ease: [0.2, 0.8, 0.2, 1] }}
        />
      </svg>
      <span className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[28px] font-medium leading-none tabular-nums text-ink">
          {score}
        </span>
        <span className="text-[9px] uppercase tracking-wider text-stone mt-1">
          completo
        </span>
      </span>
    </div>
  );
}

function CompletenessRow({ check }: { check: Check }) {
  const { Icon, cta, label } = check;
  return (
    <a
      href={cta?.href ?? "#/"}
      className={cn(
        "group flex items-center gap-2.5 rounded-card bg-canvas p-3 border border-ink/[0.06] hover:border-ink/15 transition-colors duration-180",
      )}
    >
      <span
        aria-hidden
        className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-surface text-stone group-hover:text-ink transition-colors shrink-0"
      >
        <Icon size={12} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="text-sm text-ink truncate">{label}</div>
      </div>
      <span className="text-xs text-stone group-hover:text-ink inline-flex items-center gap-0.5 transition-colors shrink-0 whitespace-nowrap">
        {cta?.label ?? "Añadir"}
        <ArrowRight size={10} className="shrink-0" />
      </span>
    </a>
  );
}

// Optional compact variant for the home/topbar — exports for future use.
export function CompletenessPill() {
  const summary = useQuery({
    queryKey: queryKeys.universe.summary,
    queryFn: () => universe.summary(),
  });
  if (!summary.data) return null;
  const counts = summary.data.counts;
  const total = 7;
  const done =
    (summary.data.headline ? 1 : 0) +
    (summary.data.summary ? 1 : 0) +
    (counts.experiences >= 1 ? 1 : 0) +
    (counts.educations >= 1 ? 1 : 0) +
    (counts.skills >= 5 ? 1 : 0) +
    (counts.languages >= 1 ? 1 : 0);
  const score = Math.round((done / total) * 100);
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-stone">
      <CheckCircle2
        size={12}
        className={cn(
          score >= 80 ? "text-leaf-ink" : score >= 50 ? "text-sunbeam-ink" : "text-stone",
        )}
      />
      <span>{score}% completo</span>
    </span>
  );
}

