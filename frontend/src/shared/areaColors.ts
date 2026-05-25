/**
 * Canonical colour + label maps for semantic AREAS.
 *
 * The graph clusters nodes by area (backend / frontend / cloud / ai_ml / …),
 * mirroring the backend taxonomy in `area_keywords.py`. In the constellation,
 * **colour encodes the area** (the cluster) and the white pictogram encodes the
 * entity kind — so a region of one hue with mixed glyphs reads as "my backend
 * stack: these skills, that project, this role".
 *
 * Keys match the backend `SOFTWARE_AREA_KEYWORDS` keys, plus two synthetic
 * buckets: `general` (no area matched) and `documents` (generated CVs/letters).
 */

export const AREA_COLORS: Record<string, string> = {
  backend: "#4f7cff",
  frontend: "#ec4899",
  fullstack: "#8b5cf6",
  devops: "#f97316",
  cloud: "#0ea5e9",
  platform: "#14b8a6",
  mobile: "#22c55e",
  ai_ml: "#a855f7",
  llm_agents: "#d946ef",
  data_eng: "#eab308",
  security: "#ef4444",
  general: "#94a3b8",
  documents: "#64748b",
};

export const AREA_LABELS: Record<string, string> = {
  backend: "Backend",
  frontend: "Frontend",
  fullstack: "Fullstack",
  devops: "DevOps",
  cloud: "Cloud",
  platform: "Plataforma",
  mobile: "Móvil",
  ai_ml: "IA / ML",
  llm_agents: "Agentes LLM",
  data_eng: "Datos",
  security: "Seguridad",
  general: "General",
  documents: "Documentos",
};

/** Stable order for legends and deterministic island placement. */
export const AREA_ORDER: string[] = [
  "backend",
  "frontend",
  "fullstack",
  "ai_ml",
  "llm_agents",
  "data_eng",
  "cloud",
  "devops",
  "platform",
  "mobile",
  "security",
  "general",
  "documents",
];

export const DEFAULT_AREA = "general";

/** Resolve the cluster key for a node from its area + kind. */
export function areaKey(area: string | null | undefined, kind?: string): string {
  if (kind === "document") return "documents";
  if (area && area in AREA_COLORS) return area;
  return DEFAULT_AREA;
}

export function colorForArea(area: string | null | undefined): string {
  return AREA_COLORS[area ?? DEFAULT_AREA] ?? AREA_COLORS[DEFAULT_AREA];
}

export function labelForArea(area: string | null | undefined): string {
  return AREA_LABELS[area ?? DEFAULT_AREA] ?? AREA_LABELS[DEFAULT_AREA];
}
