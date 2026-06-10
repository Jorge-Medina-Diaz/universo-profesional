/**
 * AgentPageBridge (P2.E) — dual-mode pages: the page renders its classic UI
 * AND exposes itself to the agent (one `useCopilotReadable` snapshot of the
 * page state + page-scoped `useCopilotAction`s that reuse the page's own
 * mutations/state setters).
 *
 * WHY A COMPONENT AND NOT A HOOK: CopilotKit's provider is lazy
 * (CopilotProvider only mounts `<CopilotKit>` after the 3 MB bundle loads),
 * and `useCopilotReadable`/`useCopilotAction` THROW outside the provider. A
 * hook called unconditionally from a page would crash the page on first
 * paint. The bridge therefore renders nothing until `useCopilotReady()` and
 * only then mounts the (lazy) inner module that imports CopilotKit — pages
 * never gain a static dependency on the heavy chunk. Each action is mounted
 * as its own child component, so the rules of hooks hold for any list size.
 *
 * NAME-SCOPING INVARIANT: page actions are registered ONLY here (the page is
 * mounted once); global actions live ONLY in UniverseActions. Never register
 * the same action name in both.
 */
import { Suspense, lazy, useEffect } from "react";
import { enableCopilot, useCopilotReady } from "@/app/CopilotProvider";
import type { CopilotActionParams } from "./actions/types";

export interface PageBridgeReadable {
  description: string;
  value: unknown;
}

export interface PageBridgeAction {
  name: string;
  description: string;
  parameters?: CopilotActionParams;
  /** Return a short string result for the agent; return (never throw)
   *  `error: …` strings on failure. */
  handler: (args: Record<string, unknown>) => Promise<string> | string;
}

export interface AgentPageBridgeProps {
  /** Stable page identifier, prefixed onto the readable ("[page:jobs] …"). */
  pageId: string;
  readable?: PageBridgeReadable;
  actions?: PageBridgeAction[];
}

const Inner = lazy(() =>
  import("./AgentPageBridgeInner").then((m) => ({ default: m.AgentPageBridgeInner })),
);

export function AgentPageBridge(props: AgentPageBridgeProps) {
  const ready = useCopilotReady();

  // The dock already warms CopilotKit on every authed page; this keeps the
  // bridge self-sufficient if a page ever renders without the dock.
  useEffect(() => {
    enableCopilot();
  }, []);

  if (!ready) return null;
  return (
    <Suspense fallback={null}>
      <Inner {...props} />
    </Suspense>
  );
}
