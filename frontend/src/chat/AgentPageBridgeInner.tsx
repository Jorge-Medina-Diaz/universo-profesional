/**
 * AgentPageBridgeInner — the CopilotKit-importing half of AgentPageBridge,
 * lazy-loaded only after the provider is ready (see useAgentPageBridge.tsx).
 *
 * Each page action mounts as its own component so `useCopilotAction` is
 * called unconditionally per component regardless of how many actions a page
 * declares. Every action gets a subtle in-thread chip (GenericToolCard) so a
 * page tool is never invisible when the agent invokes it.
 */
import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";
import { GenericToolCard } from "./cards/GenericToolCard";
import type { AgentPageBridgeProps, PageBridgeAction, PageBridgeReadable } from "./useAgentPageBridge";

type FrontendActionInput = Parameters<typeof useCopilotAction>[0];

export function AgentPageBridgeInner({ pageId, readable, actions }: AgentPageBridgeProps) {
  return (
    <>
      {readable && <BridgeReadable pageId={pageId} readable={readable} />}
      {(actions ?? []).map((action) => (
        <BridgeAction key={action.name} action={action} />
      ))}
    </>
  );
}

function BridgeReadable({
  pageId,
  readable,
}: {
  pageId: string;
  readable: PageBridgeReadable;
}) {
  useCopilotReadable({
    description: `[page:${pageId}] ${readable.description}`,
    value: readable.value,
  });
  return null;
}

function BridgeAction({ action }: { action: PageBridgeAction }) {
  useCopilotAction({
    name: action.name,
    description: action.description,
    parameters: action.parameters ?? [],
    handler: async (args: Record<string, unknown> | undefined) =>
      action.handler(args ?? {}),
    render: ({ status }: { status?: string }) => (
      <GenericToolCard name={action.name} status={status} />
    ),
  } as FrontendActionInput);
  return null;
}
