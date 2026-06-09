/**
 * Kind-aware rich bodies for the entity ProposalCard (view mode).
 *
 * Every per-entity `propose_*` tool gets a `proposal_id` injected server-side
 * (agui_streaming.py `_PROPOSAL_TOOLS`), so the ONE card users actually see for
 * a skill / project / experience / … is `ProposalCard`. By default it lists the
 * payload as flat key/value rows. For the high-frequency, visually-structured
 * kinds we render a bespoke body instead (level bar, tech chips, highlights),
 * while edit mode + the confirm/edit/reject resolve flow stay generic.
 *
 * Returns `null` for kinds without a bespoke body so the caller falls back to
 * the generic `<dl>`. Tokens only (CSS-var palette) — never raw `dark:`.
 */
import { TrendingUp, Link as LinkIcon } from "lucide-react";
import { Badge, cn } from "@/ui";

const SKILL_LEVEL_ORDER = ["basic", "intermediate", "high", "expert"];
const SKILL_LEVEL_LABEL: Record<string, string> = {
  basic: "Básico",
  intermediate: "Intermedio",
  // tolerate both "high" and "advanced" — the rubric calibration uses "high",
  // but imports occasionally land "advanced".
  advanced: "Avanzado",
  high: "Alto",
  expert: "Experto",
  native: "Nativo",
};
const SKILL_CATEGORY_LABEL: Record<string, string> = {
  hard: "Técnica",
  soft: "Blanda",
  tool: "Herramienta",
  methodology: "Metodología",
};
const PROJECT_TYPE_LABEL: Record<string, string> = {
  side: "Personal",
  oss: "Open source",
  entrepreneurship: "Emprendimiento",
  work: "Profesional",
  academic: "Académico",
};

function levelIndex(level: string): number {
  if (level === "advanced") return SKILL_LEVEL_ORDER.indexOf("high");
  if (level === "native") return SKILL_LEVEL_ORDER.length - 1;
  return SKILL_LEVEL_ORDER.indexOf(level);
}

function cap(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

function SkillBody({ data }: { data: Record<string, unknown> }) {
  const level = String(data.level ?? "").toLowerCase();
  const idx = levelIndex(level);
  const years = typeof data.years === "number" ? data.years : undefined;
  const category = typeof data.category === "string" ? data.category : undefined;
  const lastUsed = data.last_used_year;
  // Nothing structured to show → let the caller use the generic list.
  if (!level && years === undefined && !category) return null;
  return (
    <div className="space-y-3" data-testid="skill-body">
      {level && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] uppercase tracking-wide text-stone font-medium">
              Nivel
            </span>
            <span className="text-xs text-ink font-medium">
              {SKILL_LEVEL_LABEL[level] ?? cap(level)}
            </span>
          </div>
          <div className="flex gap-1" aria-hidden>
            {SKILL_LEVEL_ORDER.map((_, i) => (
              <span
                key={i}
                className={cn(
                  "h-1.5 flex-1 rounded-full",
                  idx >= 0 && i <= idx ? "bg-leaf" : "bg-field",
                )}
              />
            ))}
          </div>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-1.5">
        {category && (
          <Badge tone="leaf" size="sm">
            {SKILL_CATEGORY_LABEL[category] ?? cap(category)}
          </Badge>
        )}
        {years !== undefined && years > 0 && (
          <Badge tone="stone" size="sm">
            {years} {years === 1 ? "año" : "años"}
          </Badge>
        )}
        {lastUsed != null && lastUsed !== "" && (
          <span className="text-xs text-stone">· visto por última vez en {String(lastUsed)}</span>
        )}
      </div>
    </div>
  );
}

function ProjectBody({ data }: { data: Record<string, unknown> }) {
  const desc = typeof data.description === "string" ? data.description : undefined;
  const role = typeof data.role === "string" ? data.role : undefined;
  const ptype = typeof data.project_type === "string" ? data.project_type : undefined;
  const stack = Array.isArray(data.tech_stack) ? data.tech_stack : [];
  const highlights = Array.isArray(data.highlights) ? data.highlights : [];
  const impact = typeof data.impact === "string" ? data.impact : undefined;
  const url = typeof data.url === "string" ? data.url : undefined;
  if (!desc && !role && !ptype && stack.length === 0 && highlights.length === 0 && !impact && !url)
    return null;
  return (
    <div className="space-y-3" data-testid="project-body">
      {desc && (
        <p className="text-sm text-ink leading-relaxed line-clamp-3">{desc}</p>
      )}
      {(role || ptype) && (
        <div className="flex flex-wrap gap-1.5">
          {role && (
            <Badge tone="nova" size="sm">
              {role}
            </Badge>
          )}
          {ptype && (
            <Badge tone="stone" size="sm">
              {PROJECT_TYPE_LABEL[ptype] ?? cap(ptype)}
            </Badge>
          )}
        </div>
      )}
      {stack.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {stack.map((t, i) => (
            <span
              key={i}
              className="text-[11px] px-2 py-0.5 rounded-full bg-leaf-soft text-leaf-ink"
            >
              {String(t)}
            </span>
          ))}
        </div>
      )}
      {highlights.length > 0 && (
        <ul className="space-y-1">
          {highlights.map((h, i) => (
            <li key={i} className="flex gap-2 text-xs text-ink">
              <span className="mt-1.5 h-1 w-1 rounded-full bg-leaf shrink-0" aria-hidden />
              <span className="break-words">{String(h)}</span>
            </li>
          ))}
        </ul>
      )}
      {impact && (
        <div className="flex items-start gap-2 rounded-md bg-sunbeam-soft px-3 py-2">
          <TrendingUp size={13} className="text-sunbeam-ink mt-0.5 shrink-0" aria-hidden />
          <span className="text-xs text-sunbeam-ink break-words">{impact}</span>
        </div>
      )}
      {url && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-nova-ink hover:underline break-all"
        >
          <LinkIcon size={12} aria-hidden /> {url.replace(/^https?:\/\//, "")}
        </a>
      )}
    </div>
  );
}

/**
 * Bespoke view-mode body for a proposed entity, or `null` to fall back to the
 * generic key/value list. Only the high-frequency structured kinds are
 * specialised; everything else stays on the generic renderer.
 */
export function entityRichBody(
  entityType: string,
  data: Record<string, unknown>,
): React.ReactElement | null {
  // Gate emptiness HERE (not inside the sub-components) so the caller's
  // `richBody ?? <generic dl>` fallback fires when there's nothing structured
  // to show — a sub-component that returns null at render would suppress both.
  if (entityType === "skill") {
    const hasData =
      (typeof data.level === "string" && data.level) ||
      (typeof data.years === "number" && data.years > 0) ||
      (typeof data.category === "string" && data.category);
    return hasData ? <SkillBody data={data} /> : null;
  }
  if (entityType === "project") {
    const hasData =
      (typeof data.description === "string" && data.description) ||
      (typeof data.role === "string" && data.role) ||
      (typeof data.project_type === "string" && data.project_type) ||
      (Array.isArray(data.tech_stack) && data.tech_stack.length > 0) ||
      (Array.isArray(data.highlights) && data.highlights.length > 0) ||
      (typeof data.impact === "string" && data.impact) ||
      (typeof data.url === "string" && data.url);
    return hasData ? <ProjectBody data={data} /> : null;
  }
  return null;
}
