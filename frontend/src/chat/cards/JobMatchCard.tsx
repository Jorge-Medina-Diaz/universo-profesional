/**
 * Visual scorecard for the agent's match_job_to_profile result.
 *
 * The agent invokes `present_job_match` after running the MCP tool. We render
 * a circular score gauge, strengths/gaps lists, and ATS keyword chips. The
 * user can ask the agent to either generate a CV or drop the result.
 */
import { motion } from "motion/react";
import { Sparkles, CheckCircle2, AlertCircle, Wand2 } from "lucide-react";
import { Badge, Button, ChatMessageMotion, cn } from "@/ui";

export interface JobMatchCardProps {
  matchScore: number;
  strengths: string[];
  gaps: string[];
  suggestedKeywords?: string[];
  jobTitle?: string;
  company?: string;
  onGenerate?: () => void;
  onDismiss?: () => void;
}

export function JobMatchCard({
  matchScore,
  strengths,
  gaps,
  suggestedKeywords = [],
  jobTitle,
  company,
  onGenerate,
  onDismiss,
}: JobMatchCardProps) {
  const tone =
    matchScore >= 75
      ? "leaf"
      : matchScore >= 50
        ? "sunbeam"
        : "amber";
  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface p-5 my-3 max-w-lg shadow-soft border border-ink/[0.06]">
        <div className="flex items-start gap-4 mb-4">
          <ScoreGauge score={matchScore} tone={tone} />
          <div className="flex-1 min-w-0 space-y-1">
            <Badge tone={tone} size="sm">
              {scoreLabel(matchScore)}
            </Badge>
            {jobTitle && (
              <h4 className="font-medium text-base text-ink leading-tight">
                {jobTitle}
              </h4>
            )}
            {company && <p className="text-sm text-stone">{company}</p>}
            <p className="text-xs text-stone">
              {strengths.length} solapamientos · {gaps.length} gaps
            </p>
          </div>
        </div>

        {strengths.length > 0 && (
          <Section title="Tus fortalezas" Icon={CheckCircle2} iconBg="bg-leaf-soft text-leaf-ink">
            <div className="flex flex-wrap gap-1.5">
              {strengths.slice(0, 12).map((s) => (
                <span
                  key={s}
                  className="text-xs rounded-tag bg-leaf-soft text-leaf-ink px-2.5 py-1"
                >
                  {s}
                </span>
              ))}
              {strengths.length > 12 && (
                <Badge tone="stone" size="sm">
                  +{strengths.length - 12}
                </Badge>
              )}
            </div>
          </Section>
        )}

        {gaps.length > 0 && (
          <Section
            title="Gaps a tener en cuenta"
            Icon={AlertCircle}
            iconBg="bg-sunbeam-soft text-sunbeam-ink"
          >
            <div className="flex flex-wrap gap-1.5">
              {gaps.slice(0, 12).map((g) => (
                <span
                  key={g}
                  className="text-xs rounded-tag bg-canvas border border-dashed border-ink/15 text-stone px-2.5 py-1"
                >
                  {g}
                </span>
              ))}
              {gaps.length > 12 && (
                <Badge tone="stone" size="sm">
                  +{gaps.length - 12}
                </Badge>
              )}
            </div>
          </Section>
        )}

        {suggestedKeywords.length > 0 && (
          <Section title="Keywords ATS sugeridos" Icon={Sparkles} iconBg="bg-canvas text-ink border border-ink/10">
            <div className="flex flex-wrap gap-1.5">
              {suggestedKeywords.slice(0, 10).map((k) => (
                <span
                  key={k}
                  className="text-[11px] rounded-tag bg-canvas text-ink px-2 py-0.5 border border-ink/10"
                >
                  {k}
                </span>
              ))}
            </div>
          </Section>
        )}

        {(onGenerate || onDismiss) && (
          <div className="flex gap-2 mt-5 pt-4 border-t border-ink/5">
            {onGenerate && (
              <Button
                size="sm"
                onClick={onGenerate}
                leadingIcon={<Wand2 size={14} />}
              >
                Generar CV adaptado
              </Button>
            )}
            {onDismiss && (
              <Button size="sm" variant="ghost" onClick={onDismiss}>
                Cerrar
              </Button>
            )}
          </div>
        )}
      </div>
    </ChatMessageMotion>
  );
}

function Section({
  title,
  Icon,
  iconBg,
  children,
}: {
  title: string;
  Icon: typeof CheckCircle2;
  iconBg: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mt-4 first:mt-0">
      <div className="flex items-center gap-2 mb-2">
        <span
          aria-hidden
          className={cn(
            "inline-flex items-center justify-center w-6 h-6 rounded-full shrink-0",
            iconBg,
          )}
        >
          <Icon size={12} />
        </span>
        <span className="text-xs font-medium uppercase tracking-wider text-stone">
          {title}
        </span>
      </div>
      {children}
    </div>
  );
}

function ScoreGauge({
  score,
  tone,
}: {
  score: number;
  tone: "leaf" | "sunbeam" | "amber";
}) {
  const safe = Math.max(0, Math.min(100, score));
  const radius = 30;
  const circumference = 2 * Math.PI * radius;
  const dash = (safe / 100) * circumference;
  const stroke =
    tone === "leaf" ? "var(--color-leafy-green)" :
    tone === "sunbeam" ? "var(--color-sunbeam-yellow)" :
    "#f59e0b";
  return (
    <div className="relative shrink-0">
      <svg width="76" height="76" viewBox="0 0 76 76" aria-hidden>
        <circle
          cx="38"
          cy="38"
          r={radius}
          fill="none"
          stroke="rgba(0,0,0,0.06)"
          strokeWidth="6"
        />
        <motion.circle
          cx="38"
          cy="38"
          r={radius}
          fill="none"
          stroke={stroke}
          strokeWidth="6"
          strokeLinecap="round"
          transform="rotate(-90 38 38)"
          initial={{ strokeDasharray: `0 ${circumference}` }}
          animate={{ strokeDasharray: `${dash} ${circumference}` }}
          transition={{ duration: 0.9, ease: [0.2, 0.8, 0.2, 1] }}
        />
      </svg>
      <span className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[22px] font-medium leading-none tabular-nums text-ink">
          {safe}
        </span>
        <span className="text-[9px] uppercase tracking-wider text-stone mt-0.5">
          /100
        </span>
      </span>
    </div>
  );
}

function scoreLabel(score: number): string {
  if (score >= 85) return "Match excelente";
  if (score >= 70) return "Match bueno";
  if (score >= 50) return "Match parcial";
  return "Match débil";
}
