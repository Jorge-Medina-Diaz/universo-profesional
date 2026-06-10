/**
 * AgentSharedState — the AG-UI shared state the backend streams during a run
 * (STATE_SNAPSHOT after RUN_STARTED, then RFC-6902 STATE_DELTAs on every
 * transition; see backend/src/agents/interfaces/state_emitter.py).
 *
 * This module is intentionally free of CopilotKit imports so the humanizing
 * helpers can be consumed by always-mounted chrome (FloatingChat's status chip
 * via the Zustand store) without pulling the heavy chat bundle.
 */
import type { ThinkingStep } from "./ThinkingSteps";

/** The agent name pinned by the backend AG-UI runtime (`/agui/info`). */
export const AGENT_NAME = "universe_coordinator";

export type AgentStatus =
  | "thinking"
  | "routing"
  | "working"
  | "using_tool"
  | "awaiting_confirmation"
  | "answering"
  | "idle";

export type ActiveSpecialist =
  | "entity_curator"
  | "onboarding_specialist"
  | "discovery_coach"
  | "profile_analyst"
  | "document_coach"
  | "job_strategist"
  | "domain_expert";

export interface AgentSharedState {
  v: 1;
  agent_status: AgentStatus;
  current_intent: string | null;
  active_specialist: ActiveSpecialist | null;
  current_tool: string | null;
  pending_proposal: string | null;
}

/** Humanized specialist nouns — read as "Consultando a tu {noun}…". */
const SPECIALIST_NOUNS: Record<ActiveSpecialist, string> = {
  entity_curator: "curador del universo",
  onboarding_specialist: "guía de bienvenida",
  discovery_coach: "coach de descubrimiento",
  profile_analyst: "analista de perfil",
  document_coach: "coach de documentos",
  job_strategist: "estratega de empleo",
  domain_expert: "experto del dominio",
};

/** Spanish labels for the most common tools; anything else gets a generic
 *  "Usando {tool}…" so a new backend tool is never raw-snake-cased. */
const TOOL_LABELS: Record<string, string> = {
  universe_retrieve: "Buscando en tu universo…",
  match_job_to_profile: "Calculando match con la oferta…",
  get_universe_shape: "Analizando la forma de tu universo…",
  find_gaps: "Buscando huecos en tu perfil…",
  search_rubrics: "Consultando criterios profesionales…",
  list_reminders: "Revisando recordatorios…",
  list_pending_curation: "Revisando pendientes de curación…",
  generate_document: "Generando el documento…",
  record_feedback: "Anotando tu feedback…",
  navigate_to: "Llevándote a la página…",
  present_form: "Preparando el formulario…",
};

export function toolLabel(tool: string): string {
  return TOOL_LABELS[tool] ?? `Usando ${tool.replace(/_/g, " ")}…`;
}

function specialistLabel(specialist: ActiveSpecialist | null): string {
  if (!specialist) return "Trabajando en ello…";
  const noun = SPECIALIST_NOUNS[specialist];
  return noun
    ? `Consultando a tu ${noun}…`
    : `Consultando a ${String(specialist).replace(/_/g, " ")}…`;
}

/** True when the state payload looks like the v1 shape the backend emits. */
function isSharedState(state: unknown): state is AgentSharedState {
  return (
    !!state &&
    typeof state === "object" &&
    (state as { v?: unknown }).v === 1 &&
    typeof (state as { agent_status?: unknown }).agent_status === "string"
  );
}

/**
 * One-line humanized status for the dock chip. Null when idle/unknown —
 * callers hide the chip entirely in that case.
 */
export function agentStatusLabel(state: unknown): string | null {
  if (!isSharedState(state)) return null;
  switch (state.agent_status) {
    case "thinking":
      return "Pensando…";
    case "routing":
      return "Decidiendo cómo ayudarte…";
    case "working":
      return specialistLabel(state.active_specialist);
    case "using_tool":
      return state.current_tool ? toolLabel(state.current_tool) : "Usando una herramienta…";
    case "awaiting_confirmation":
      return "Esperando tu confirmación…";
    case "answering":
      return "Redactando respuesta…";
    default:
      return null; // idle
  }
}

/**
 * Map the streamed shared state onto the ThinkingSteps pipeline. Earlier
 * phases render as done, the current one pulses (when the run is in
 * progress); a finished run shows everything as done.
 */
export function thinkingStepsFromState(
  state: unknown,
  inProgress: boolean,
): ThinkingStep[] {
  if (!isSharedState(state)) return [];
  const s = state.agent_status;
  if (s === "idle") return [];

  const steps: ThinkingStep[] = [];
  const push = (id: string, label: string, active: boolean) =>
    steps.push({ id, label, status: active && inProgress ? "active" : "done" });

  push("thinking", "Pensando…", s === "thinking");
  if (state.active_specialist) {
    push("specialist", specialistLabel(state.active_specialist), s === "routing" || s === "working");
  } else if (s === "routing") {
    push("routing", "Decidiendo cómo ayudarte…", true);
  }
  if (state.current_tool) {
    push("tool", toolLabel(state.current_tool), s === "using_tool");
  }
  if (s === "awaiting_confirmation" || state.pending_proposal) {
    push("confirm", "Esperando tu confirmación…", s === "awaiting_confirmation");
  }
  if (s === "answering") {
    push("answer", "Redactando respuesta…", true);
  }
  return steps;
}
