/**
 * GlobalAgentDock — the agent, everywhere.
 *
 * Mounted ONCE in the authenticated Layout so EVERY page has a persistent,
 * collapsible chat dock. It renders the shared {@link AgentChatMount} (the same
 * FloatingChat + CopilotSurface used by the home/universe surfaces), so
 * streaming + HITL cards behave identically and the conversation follows the
 * user across pages (backend pins thread_id = main-<user_id>).
 *
 * It steps aside on routes that already mount AgentChatMount themselves (home,
 * universe, onboarding) so exactly one CopilotChat is mounted at rest — two
 * would double-register the propose_ and present_ actions.
 */
import { useHashRoute } from "@/shared/useHashRoute";
import { AgentChatMount } from "@/chat/AgentChatMount";

/** Routes whose page mounts its own AgentChatMount — the dock steps aside. */
function ownsChat(path: string): boolean {
  return (
    path === "/" || path.startsWith("/universe") || path === "/onboarding/chat"
  );
}

export function GlobalAgentDock() {
  const path = useHashRoute();
  if (ownsChat(path)) return null;
  return <AgentChatMount />;
}
