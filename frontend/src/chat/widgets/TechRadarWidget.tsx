/**
 * TechRadarWidget — visualizes the user's polyglot shape.
 *
 * Data shape from `get_universe_shape`:
 *   {
 *     shape_type: "I" | "T" | "π" | "M" | "none",
 *     primary_areas: string[],
 *     secondary_areas: string[],
 *     strengths: [{
 *       area, depth_years, breadth_count,
 *       recency_months, confidence, is_primary
 *     }],
 *     artifacts_count?: number,
 *   }
 *
 * Renders a custom SVG radar (no recharts dep): one axis per area, radius
 * by depth_years (capped at 10), color shaded by recency (fresh = leaf,
 * stale = amber/red), primaries highlighted.
 */
import { Badge } from "@/ui";

interface AreaStrengthData {
  area: string;
  depth_years?: number;
  breadth_count?: number;
  recency_months?: number | null;
  confidence?: number;
  is_primary?: boolean;
}

interface SignalEntry {
  heading?: string;
  body_excerpt?: string;
  confidence?: number;
  rubric_slug?: string;
}

interface AreaSignalGroup {
  own?: SignalEntry[];
  aspire?: SignalEntry[];
  avoid?: SignalEntry[];
}

interface TechRadarData {
  shape_type?: "I" | "T" | "π" | "M" | "none";
  primary_areas?: string[];
  secondary_areas?: string[];
  strengths?: AreaStrengthData[];
  artifacts_count?: number;
  signals_by_area?: Record<string, AreaSignalGroup>;
}

const AREA_LABEL: Record<string, string> = {
  backend: "Backend",
  frontend: "Frontend",
  fullstack: "Fullstack",
  devops: "DevOps",
  cloud: "Cloud",
  platform: "Platform",
  mobile: "Mobile",
  ai_ml: "AI / ML",
  llm_agents: "LLM Agents",
  data_eng: "Data Eng",
  security: "Security",
  other: "Otro",
};

const SHAPE_TONE: Record<string, { tone: string; label: string }> = {
  I: { tone: "bg-leaf-soft text-leaf-ink", label: "I-shape · especialista" },
  T: { tone: "bg-sunbeam-soft text-sunbeam-ink", label: "T-shape · profundo + ancho" },
  π: { tone: "bg-sunbeam-soft text-sunbeam-ink", label: "π-shape · dos fortalezas" },
  M: { tone: "bg-amber-100 text-amber-800", label: "M-shape · polyglot amplio" },
  none: { tone: "bg-black/[0.05] text-stone", label: "Sin perfil aún" },
};

const MAX_DEPTH = 10; // years cap for radius scaling

export function TechRadarWidget({ data }: { data: TechRadarData }) {
  const strengths = (data.strengths ?? []).slice(0, 8);
  const shapeMeta = SHAPE_TONE[data.shape_type ?? "none"] ?? SHAPE_TONE.none;
  const primary = data.primary_areas ?? [];
  const secondary = data.secondary_areas ?? [];

  if (!strengths.length) {
    return (
      <div className="flex flex-col gap-2 text-sm text-stone">
        <p>
          Tu radar está vacío. Añade 3-5 skills y 1 proyecto para que el sistema
          pueda detectar tu shape.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <Badge tone="stone" className={shapeMeta.tone}>
          {shapeMeta.label}
        </Badge>
        {data.artifacts_count !== undefined ? (
          <span className="text-[11px] text-stone tabular-nums">
            {data.artifacts_count} artifact{data.artifacts_count === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>

      <RadarSvg strengths={strengths} />

      <AreaList strengths={strengths} primaries={primary} secondaries={secondary} />

      {data.signals_by_area ? (
        <SignalsBlock signalsByArea={data.signals_by_area} primary={primary} />
      ) : null}
    </div>
  );
}

function SignalsBlock({
  signalsByArea,
  primary,
}: {
  signalsByArea: Record<string, AreaSignalGroup>;
  primary: string[];
}) {
  const areas = primary.length > 0 ? primary : Object.keys(signalsByArea);
  const visible = areas.filter((a) => signalsByArea[a]);
  if (visible.length === 0) return null;
  return (
    <div className="flex flex-col gap-3 border-t border-black/[0.05] pt-3">
      <div className="text-[11px] uppercase tracking-wide text-stone font-medium">
        Signals concretos
      </div>
      {visible.map((area) => {
        const group = signalsByArea[area];
        return (
          <div key={area} className="flex flex-col gap-1.5">
            <div className="text-xs font-medium text-ink">
              {AREA_LABEL[area] ?? area}
            </div>
            {group.own && group.own.length > 0 ? (
              <SignalLine label="Dominas" tone="leaf" items={group.own.slice(0, 3)} />
            ) : null}
            {group.aspire && group.aspire.length > 0 ? (
              <SignalLine
                label="Te falta"
                tone="amber"
                items={group.aspire.slice(0, 3)}
              />
            ) : null}
            {group.avoid && group.avoid.length > 0 ? (
              <SignalLine
                label="Anti-patrón detectado"
                tone="danger"
                items={group.avoid.slice(0, 2)}
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function SignalLine({
  label,
  tone,
  items,
}: {
  label: string;
  tone: "leaf" | "amber" | "danger";
  items: SignalEntry[];
}) {
  const dotColor =
    tone === "leaf"
      ? "bg-leaf-ink"
      : tone === "amber"
        ? "bg-amber-500"
        : "bg-rose-500";
  return (
    <div className="flex flex-col gap-0.5 text-[11px]">
      <span className="uppercase tracking-wide text-stone font-medium text-[10px]">
        {label}
      </span>
      <ul className="flex flex-col gap-0.5">
        {items.map((it, i) => (
          <li key={i} className="flex items-start gap-1.5 leading-snug">
            <span
              className={`inline-block w-1.5 h-1.5 rounded-full mt-1 shrink-0 ${dotColor}`}
            />
            <span className="text-ink/85">
              {it.heading ?? it.body_excerpt ?? "—"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RadarSvg({ strengths }: { strengths: AreaStrengthData[] }) {
  const n = strengths.length;
  if (n < 3) {
    // Radar needs ≥3 axes; fall back to bars below
    return null;
  }
  const size = 220;
  const cx = size / 2;
  const cy = size / 2;
  const maxR = (size / 2) - 28;

  // Pre-compute axis endpoints
  const axes = strengths.map((s, i) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const xEnd = cx + Math.cos(angle) * maxR;
    const yEnd = cy + Math.sin(angle) * maxR;
    return { angle, xEnd, yEnd, label: AREA_LABEL[s.area] ?? s.area, area: s.area };
  });

  // Polygon points (each area's depth normalized into [0..1] * maxR)
  const points = strengths
    .map((s, i) => {
      const depth = Math.min(MAX_DEPTH, s.depth_years ?? 0);
      const r = (depth / MAX_DEPTH) * maxR;
      const a = axes[i].angle;
      return `${cx + Math.cos(a) * r},${cy + Math.sin(a) * r}`;
    })
    .join(" ");

  // Concentric rings: 2.5, 5, 7.5, 10 years
  const rings = [0.25, 0.5, 0.75, 1].map((f) => (f * maxR).toFixed(1));

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${size} ${size}`}
      className="overflow-visible"
      aria-label="Tech radar"
    >
      {/* rings */}
      {rings.map((r, idx) => (
        <circle
          key={r}
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="currentColor"
          className="text-black/[0.06]"
          strokeDasharray={idx === rings.length - 1 ? undefined : "2 3"}
        />
      ))}
      {/* axes */}
      {axes.map((a, i) => (
        <line
          key={i}
          x1={cx}
          y1={cy}
          x2={a.xEnd}
          y2={a.yEnd}
          stroke="currentColor"
          className="text-black/[0.08]"
        />
      ))}
      {/* polygon */}
      <polygon
        points={points}
        fill="currentColor"
        className="text-ink/15"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinejoin="round"
      />
      {/* per-vertex dots, color by recency */}
      {strengths.map((s, i) => {
        const a = axes[i].angle;
        const depth = Math.min(MAX_DEPTH, s.depth_years ?? 0);
        const r = (depth / MAX_DEPTH) * maxR;
        const x = cx + Math.cos(a) * r;
        const y = cy + Math.sin(a) * r;
        const tone = recencyColor(s.recency_months ?? null);
        return (
          <circle
            key={s.area}
            cx={x}
            cy={y}
            r={s.is_primary ? 5 : 3.5}
            className={tone.fill}
            stroke="white"
            strokeWidth={1.5}
          />
        );
      })}
      {/* labels */}
      {axes.map((a) => {
        const lx = cx + Math.cos(a.angle) * (maxR + 14);
        const ly = cy + Math.sin(a.angle) * (maxR + 14);
        return (
          <text
            key={a.area}
            x={lx}
            y={ly}
            fontSize={10}
            fill="currentColor"
            textAnchor="middle"
            dominantBaseline="middle"
            className="text-ink/80"
          >
            {a.label}
          </text>
        );
      })}
    </svg>
  );
}

function AreaList({
  strengths,
  primaries,
  secondaries,
}: {
  strengths: AreaStrengthData[];
  primaries: string[];
  secondaries: string[];
}) {
  const primSet = new Set(primaries);
  const secSet = new Set(secondaries);
  return (
    <div className="grid grid-cols-2 gap-3 text-[11px]">
      <div className="flex flex-col gap-1.5">
        <div className="uppercase tracking-wide text-stone font-medium">Primarias</div>
        {strengths.filter((s) => primSet.has(s.area)).length === 0 ? (
          <div className="text-stone italic">—</div>
        ) : (
          strengths
            .filter((s) => primSet.has(s.area))
            .map((s) => <AreaRow key={s.area} s={s} bold />)
        )}
      </div>
      <div className="flex flex-col gap-1.5">
        <div className="uppercase tracking-wide text-stone font-medium">Secundarias</div>
        {strengths.filter((s) => secSet.has(s.area)).length === 0 ? (
          <div className="text-stone italic">—</div>
        ) : (
          strengths
            .filter((s) => secSet.has(s.area))
            .map((s) => <AreaRow key={s.area} s={s} bold={false} />)
        )}
      </div>
    </div>
  );
}

function AreaRow({ s, bold }: { s: AreaStrengthData; bold: boolean }) {
  const recency = recencyLabel(s.recency_months ?? null);
  return (
    <div className="flex items-center gap-2 leading-snug">
      <span
        className={`inline-block w-1.5 h-1.5 rounded-full ${recencyColor(s.recency_months ?? null).bg}`}
      />
      <span className={bold ? "font-medium text-ink" : "text-ink/85"}>
        {AREA_LABEL[s.area] ?? s.area}
      </span>
      <span className="text-stone tabular-nums">
        {(s.depth_years ?? 0).toFixed(1)}y · b{s.breadth_count ?? 0}
        {recency ? ` · ${recency}` : ""}
      </span>
    </div>
  );
}

function recencyColor(months: number | null) {
  if (months === null) return { fill: "fill-stone/40", bg: "bg-stone/40" };
  if (months <= 12) return { fill: "fill-leaf-ink", bg: "bg-leaf-ink" };
  if (months <= 36) return { fill: "fill-amber-500", bg: "bg-amber-500" };
  return { fill: "fill-rose-500", bg: "bg-rose-500" };
}

function recencyLabel(months: number | null): string | null {
  if (months === null) return null;
  if (months <= 12) return "fresco";
  if (months <= 24) return "<2a";
  if (months <= 36) return "<3a";
  return ">3a";
}
