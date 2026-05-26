import { useCopilotAction } from "@copilotkit/react-core";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/shared/queryKeys";
import { EntryCard, ResolvedEntryChip } from "../cards/EntryCard";
import type { SavingState, UpsertResponse, CopilotActionParams } from "./types";
import { coherenceUpsert } from "./shared";

interface EntityActionConfig<TArgs> {
  toolName: string;
  description: string;
  entityKind: string;
  cardTitle: (args: TArgs) => string;
  parameters: CopilotActionParams;
  buildPayload?: (args: TArgs) => Record<string, unknown>;
  /** Optional card override. Falls back to EntryCard. */
  renderCard?: (ctx: {
    args: TArgs;
    pending: boolean;
    onConfirm: () => Promise<void>;
    onReject: () => void;
  }) => React.ReactElement;
}

export function useEntityAction<TArgs extends Record<string, unknown>>(
  config: EntityActionConfig<TArgs>,
  saving: SavingState,
  setSaving: (s: SavingState) => void,
  setLastOutcome: (o: { kind: string; resp: UpsertResponse } | null) => void,
  qc: ReturnType<typeof useQueryClient>,
) {
  useCopilotAction({
    name: config.toolName,
    description: config.description,
    parameters: config.parameters,
    renderAndWaitForResponse: ({
      args,
      respond,
      status,
      result,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
      status?: string;
      result?: unknown;
    }) => {
      // Once the tool call is resolved, show a terminal confirmation instead of
      // the interactive card — otherwise a confirmed card keeps its buttons (or
      // a stuck "Guardando" spinner when a follow-up run fails).
      if (status === "complete") {
        return (
          <ResolvedEntryChip
            kind={config.entityKind}
            title={config.cardTitle(args as TArgs)}
            result={typeof result === "string" ? result : undefined}
          />
        );
      }
      const pending = saving === config.entityKind;
      const onConfirm = async () => {
        setSaving(config.entityKind);
        try {
          const payload = config.buildPayload
            ? config.buildPayload(args as TArgs)
            : (args as Record<string, unknown>);
          const resp = await coherenceUpsert(config.entityKind, payload);
          qc.invalidateQueries({ queryKey: queryKeys.universe.all });
          qc.invalidateQueries({ queryKey: queryKeys.coherence.changes });
          setLastOutcome({ kind: config.entityKind, resp });
          respond?.(JSON.stringify(resp));
        } catch (e) {
          respond?.(`Error: ${(e as Error).message}`);
        } finally {
          setSaving(null);
        }
      };
      const onReject = () => respond?.("Rejected by user.");
      if (config.renderCard) {
        return config.renderCard({
          args: args as TArgs,
          pending,
          onConfirm,
          onReject,
        });
      }
      return (
        <EntryCard
          title={config.cardTitle(args as TArgs)}
          kind={config.entityKind}
          details={args as Record<string, unknown>}
          pending={pending}
          onConfirm={onConfirm}
          onReject={onReject}
        />
      );
    },
  });
}
