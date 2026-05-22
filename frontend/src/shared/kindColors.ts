/**
 * Canonical colour + label maps for universe entity kinds.
 *
 * Single source of truth shared by the graph renderer (GraphView), the
 * universe page (filters, outline), and any future consumer. Keeping it
 * here avoids the colour palette drifting between the graph and the rest
 * of the app.
 */

export const KIND_COLORS: Record<string, string> = {
  skill: "#4f7cff",
  project: "#10b981",
  experience: "#f59e0b",
  education: "#a855f7",
  certification: "#0ea5e9",
  course: "#14b8a6",
  language: "#f43f5e",
  achievement: "#eab308",
  interest: "#84cc16",
  artifact: "#8b5cf6",
  architecture_decision: "#ec4899",
};

export const DEFAULT_KIND_COLOR = "#94a3b8";

export const KIND_LABELS: Record<string, string> = {
  skill: "Competencia",
  project: "Proyecto",
  experience: "Experiencia",
  education: "Formación",
  certification: "Certificación",
  course: "Curso",
  language: "Idioma",
  achievement: "Logro",
  interest: "Interés",
  artifact: "Artifact",
  architecture_decision: "ADR",
};

export function kindColor(kind: string): string {
  return KIND_COLORS[kind] ?? DEFAULT_KIND_COLOR;
}
