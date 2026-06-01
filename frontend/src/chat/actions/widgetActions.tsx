import { useEffect } from "react";
import { useCopilotAction } from "@copilotkit/react-core";
import { useQueryClient } from "@tanstack/react-query";
import { useChatState, type FocusEntity, type WidgetKind } from "../state";
import { useGraphLensState, type GraphLensMode } from "@/graph/lensState";

import { ProgressCard } from "../cards/ProgressCard";
import { UploadInlineCard } from "../cards/UploadInlineCard";
import type { SavingState, UpsertResponse, CopilotActionParams } from "./types";

export function useWidgetActions(
  _saving: SavingState,
  _setSaving: (s: SavingState) => void,
  _setLastOutcome: (o: { kind: string; resp: UpsertResponse } | null) => void,
  _qc: ReturnType<typeof useQueryClient>,
) {
  useCopilotAction({
    name: "set_chat_focus",
    description:
      "Signal which entity the agent is currently reasoning about; the frontend uses this to highlight / pre-select it.",
    parameters: [
      { name: "entity", type: "string", required: true },
      { name: "id", type: "string", required: true },
      { name: "meta", type: "object" },
    ] satisfies CopilotActionParams,
    handler: async (args: Record<string, unknown>) => {
      useChatState.getState().setFocus({
        entity: (args.entity as FocusEntity) ?? null,
        id: (args.id as string) ?? null,
        meta: (args.meta as Record<string, unknown>) ?? null,
      });
      return { ok: true };
    },
  });

  useCopilotAction({
    name: "present_graph_view",
    description:
      // Only advertise modes the universe view actually renders (cluster/
      // ontology_overlay are not wired → don't tell the model to call no-ops).
      "Switch the universe graph lens: mode 'focus' (centre the graph on an entity via focus_entity_id), 'timeline' (career trajectory view) or 'outline' (structured entity outline).",
    parameters: [
      { name: "mode", type: "string", required: true },
      { name: "focus_entity_id", type: "string" },
    ] satisfies CopilotActionParams,
    handler: async (args: Record<string, unknown>) => {
      const mode = (args.mode as GraphLensMode) ?? "focus";
      useGraphLensState.getState().setLens({
        mode,
        focusEntityId: (args.focus_entity_id as string) ?? null,
      });
      return { ok: true, mode };
    },
  });

  useCopilotAction({
    name: "present_progress",
    description:
      "Display-only progress card for a long-running task (steps + state).",
    available: "frontend",
    parameters: [
      { name: "title", type: "string", required: true },
      { name: "state", type: "string", required: true },
      { name: "steps", type: "object[]", required: true },
      { name: "detail", type: "string" },
      { name: "error_message", type: "string" },
    ] satisfies CopilotActionParams,
    render: ({ args }: { args: Record<string, unknown> }) => (
      <ProgressCard
        title={(args.title as string) ?? "Tarea"}
        state={((args.state as string) ?? "running") as "running" | "done" | "error"}
        steps={(args.steps as Parameters<typeof ProgressCard>[0]["steps"]) ?? []}
        detail={args.detail as string | undefined}
        errorMessage={args.error_message as string | undefined}
      />
    ),
  });

  useCopilotAction({
    name: "present_widget",
    description:
      "Render a widget in the right-side widget pane. Use this when the user asks to VIEW / SUMMARIZE structured insight from their universe. Call the relevant read-only tool first, then invoke this with kind + title + data. Supported kinds: goals_progress, interview_qa, tech_radar, agent_patterns, signal_coverage, document_preview, job_match, cloud_coverage, data_stack_topology, security_posture, architecture_patterns, portfolio_radar, learning_trajectory.",
    available: "frontend",
    parameters: [
      { name: "kind", type: "string", required: true },
      { name: "title", type: "string", required: true },
      { name: "data", type: "object", required: true },
    ] satisfies CopilotActionParams,
    render: ({ args }: { args: Record<string, unknown> }) => (
      <PresentWidgetMarker
        kind={args.kind as WidgetKind}
        title={args.title as string}
        data={(args.data as Record<string, unknown>) ?? {}}
      />
    ),
  });

  useCopilotAction({
    name: "upload_document_inline",
    description:
      "Open an inline upload dropzone in the chat so the user can drop a PDF/image without leaving the conversation.",
    parameters: [
      { name: "purpose", type: "string", required: true },
      { name: "accept", type: "string" },
      { name: "max_bytes", type: "number" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <UploadInlineCard
        purpose={(args.purpose as string) ?? "Subir archivo"}
        accept={(args.accept as string) ?? "application/pdf"}
        maxBytes={(args.max_bytes as number) ?? 10 * 1024 * 1024}
        onComplete={(payload) => respond?.(JSON.stringify(payload))}
        onCancel={() => respond?.(JSON.stringify({ uploaded: false, cancelled: true }))}
      />
    ),
  });
}

/**
 * Tiny passive marker rendered in the chat stream when the agent emits
 * `present_widget`. The actual widget renders in the WidgetPane via zustand.
 * Pushing to the store happens once on mount; further renders are a no-op.
 */
function PresentWidgetMarker({
  kind,
  title,
  data,
}: {
  kind: WidgetKind;
  title: string;
  data: Record<string, unknown>;
}) {
  useEffect(() => {
    useChatState.getState().addWidget({ kind, title, data });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div className="text-xs text-stone italic mt-1">
      Added <span className="font-medium text-ink/80">"{title}"</span> to panel
    </div>
  );
}
