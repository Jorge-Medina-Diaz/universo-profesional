import { useCopilotAction } from "@copilotkit/react-core";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/shared/queryKeys";
import { EntryCard, ResolvedEntryChip } from "../cards/EntryCard";
import { ProposalCard, ResolvedProposalChip } from "../components/ProposalCard";
import type { SavingState, UpsertResponse, CopilotActionParams } from "./types";
import { coherenceUpsert } from "./shared";

interface EntityActionConfig<TArgs> {
  toolName: string;
  description: string;
  entityKind: string;
  cardTitle: (args: TArgs) => string;
  parameters: CopilotActionParams;
  buildPayload?: (args: TArgs) => Record<string, unknown>;
  /** Optional card override. Falls back to EntryCard / ProposalCard. */
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
      // Terminal state — once the tool call is resolved, show a quiet chip
      // instead of the interactive card.
      if (status === "complete") {
        if (args.proposal_id && typeof args.proposal_id === "string") {
          return (
            <ResolvedProposalChip
              payload={{
                proposal_id: args.proposal_id as string,
                entity_type: ((args.entity_type as string) || config.entityKind) as import("../components/ProposalCard").EntityType,
                entity_data: args as Record<string, unknown>,
                action: (args.action as string) || "create",
                confidence: (args.confidence as number) || 0.85,
                reason: (args.reason as string) || "",
              }}
              result={typeof result === "string" ? result : undefined}
            />
          );
        }
        return (
          <ResolvedEntryChip
            kind={config.entityKind}
            title={config.cardTitle(args as TArgs)}
            result={typeof result === "string" ? result : undefined}
          />
        );
      }

      // If the backend injected a rich proposal payload, render ProposalCard.
      if (args.proposal_id && typeof args.proposal_id === "string") {
        const pending = saving === config.entityKind;
        return (
          <ProposalCard
            payload={{
              proposal_id: args.proposal_id as string,
              entity_type: ((args.entity_type as string) || config.entityKind) as import("../components/ProposalCard").EntityType,
              entity_data: args as Record<string, unknown>,
              action: (args.action as string) || "create",
              confidence: (args.confidence as number) || 0.85,
              reason: (args.reason as string) || "",
            }}
            pending={pending}
            onResolved={({ action, response }) => {
              qc.invalidateQueries({ queryKey: queryKeys.universe.all });
              qc.invalidateQueries({ queryKey: queryKeys.coherence.changes });
              setLastOutcome({ kind: config.entityKind, resp: response });
              respond?.(JSON.stringify({ action, ...response }));
            }}
          />
        );
      }

      // Legacy fallback — plain EntryCard without proposal metadata.
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
