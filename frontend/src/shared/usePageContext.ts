/**
 * usePageContext — typed one-shot consumption of the context handed to a page
 * by the agent's `navigate_to(route, context)` tool (or in-app writers like
 * the kanban "CV" button / CommandPalette) via the chat store's
 * `pendingPageContext` slice. Replaces the old sessionStorage prefill hacks.
 *
 * Semantics:
 *  - The mounting page captures the context in a useState initializer (so the
 *    very first render can already use it) and the slice is cleared in a mount
 *    effect — under React StrictMode the initializer runs twice for the same
 *    mount, so a CLEARING initializer would lose the payload on the render
 *    that sticks; the effect-clear is idempotent.
 *  - The hook also subscribes to the slice, so when the agent navigates to the
 *    route the user is ALREADY on (no remount), the fresh context still lands.
 */
import { useEffect, useState } from "react";
import { useChatState } from "@/chat/state";

/** Contexts older than this are stale leftovers (a writer set the slice but
 *  navigation never happened) and are ignored. */
const MAX_AGE_MS = 5 * 60_000;

function freshContextFor(route: string): Record<string, unknown> | null {
  const pending = useChatState.getState().pendingPageContext;
  if (!pending || pending.route !== route) return null;
  if (Date.now() - pending.ts > MAX_AGE_MS) return null;
  return pending.context;
}

export function usePageContext<T>(route: string): T | null {
  const [ctx, setCtx] = useState<T | null>(() => freshContextFor(route) as T | null);
  const pending = useChatState((s) => s.pendingPageContext);

  useEffect(() => {
    if (!pending || pending.route !== route) return;
    const fresh = freshContextFor(route);
    if (fresh) setCtx(fresh as T);
    // Consume (clear) — idempotent, StrictMode-safe; also clears stale leftovers.
    useChatState.getState().consumePageContext(route);
  }, [pending, route]);

  return ctx;
}
