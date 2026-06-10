/**
 * HITL CopilotKit actions wired to the Agno backend.
 *
 * Tool names use `snake_case` to match the Agno `@tool(external_execution=True)`
 * declarations in `backend/src/agents/tools/ui_widgets.py`. The agent emits an
 * AG-UI tool-call event; CopilotKit matches by name and `renderAndWaitForResponse`
 * shows the card. After the user confirms, the card calls the universe REST API
 * (which Agno already knows about via its own `add_*` server-side tools, but we
 * persist from the client to keep the universe REST surface as the single
 * source of truth — easier to audit and reuse from the existing pages).
 */
import { useEffect, useState } from "react";
import { useCopilotChat, useCopilotAction } from "@copilotkit/react-core";
import { useQueryClient } from "@tanstack/react-query";
import { useChatState } from "../state";
import { DiffCard } from "../cards/DiffCard";
import { GenericToolCard, isSilentTool } from "../cards/GenericToolCard";
import { useEntityActions } from "./entityActions";
import { useJobActions } from "./jobActions";
import { useDocumentActions } from "./documentActions";
import { useWidgetActions } from "./widgetActions";
import { useImportActions } from "./importActions";
import { useGenericActions } from "./genericActions";
import { useInsightActions } from "./insightActions";
import { useNavigationActions } from "./navigationActions";
import { useFormActions } from "./formActions";
import type { SavingState, UpsertResponse } from "./types";

export type { CopilotActionParams, CopilotActionParam, CopilotParamType } from "./types";

export function UniverseActions() {
  const qc = useQueryClient();
  const [saving, setSaving] = useState<SavingState>(null);
  const [lastOutcome, setLastOutcome] = useState<
    { kind: string; resp: UpsertResponse } | null
  >(null);

  // Keep the module-level chat session id in sync so coherenceUpsert can
  // bind persisted entities to the current Episode (Sprint P).
  const { threadId } = useCopilotChat();
  useEffect(() => {
    useChatState.getState().setActiveSessionId(threadId ?? null);
  }, [threadId]);

  useEntityActions(saving, setSaving, setLastOutcome, qc);
  useJobActions(saving, setSaving, setLastOutcome, qc);
  useDocumentActions(saving, setSaving, setLastOutcome, qc);
  useWidgetActions(saving, setSaving, setLastOutcome, qc);
  useImportActions(saving, setSaving, setLastOutcome, qc);
  useGenericActions(saving, setSaving, setLastOutcome, qc);
  useInsightActions();
  useNavigationActions();
  useFormActions();

  // Wildcard safety net: ANY backend tool without an explicit renderer above
  // gets a subtle chip so it's never dead-silent (exact-name actions take
  // precedence). Internal reasoning reads stay quiet via isSilentTool.
  useCopilotAction({
    name: "*",
    render: ({ name, status }: { name?: string; status?: string }) => {
      if (!name || isSilentTool(name)) return <></>;
      return <GenericToolCard name={name} status={status} />;
    },
  });

  // --- Post-write feedback (DiffCard for last merge/created/suggested) ----
  // Rendered inline outside the chat surface so the user gets a tangible
  // "the engine merged X" cue right after a confirmation. The card stays
  // until the next outcome replaces it; the agent's text response covers
  // the in-chat acknowledgement.
  if (lastOutcome) {
    return (
      <div className="fixed bottom-4 right-4 z-30 pointer-events-none">
        <div className="pointer-events-auto">
          <DiffCard
            title={`${lastOutcome.kind}`}
            diffs={lastOutcome.resp.diffs}
            status={lastOutcome.resp.status}
          />
        </div>
      </div>
    );
  }
  return null;
}
