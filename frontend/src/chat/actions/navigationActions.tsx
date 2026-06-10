/**
 * Agent-driven navigation (P2.C) — the backend `navigate_to(route, context?,
 * reason?)` tool executes HERE: validate the route against a literal
 * allowlist, stash the context for the destination page (usePageContext),
 * then move the hash router. The handler returns a short string so the agent
 * knows it landed (or why it didn't — never a throw).
 */
import { useCopilotAction } from "@copilotkit/react-core";
import { GenericToolCard } from "../cards/GenericToolCard";
import { useChatState } from "../state";
import type { CopilotActionParams } from "./types";

/** Mirror of the backend tool's documented allowlist (ui_widgets.navigate_to). */
const ALLOWED_ROUTES = [
  "/",
  "/universe",
  "/jobs",
  "/documents",
  "/cv/new",
  "/notes",
  "/activity",
  "/reminders",
  "/connections",
  "/preferences",
  "/settings",
  "/goals",
] as const;

export function useNavigationActions() {
  useCopilotAction({
    name: "navigate_to",
    description:
      "Navigate the app to a page for the user, optionally carrying a context object the destination page consumes to pre-fill or focus itself.",
    parameters: [
      { name: "route", type: "string", required: true },
      { name: "context", type: "object" },
      { name: "reason", type: "string" },
    ] satisfies CopilotActionParams,
    handler: async (args: Record<string, unknown>) => {
      const route = String(args.route ?? "").trim();
      if (!(ALLOWED_ROUTES as readonly string[]).includes(route)) {
        return `error: ruta no permitida '${route}'. Rutas válidas: ${ALLOWED_ROUTES.join(", ")}.`;
      }
      const context =
        args.context && typeof args.context === "object" && !Array.isArray(args.context)
          ? (args.context as Record<string, unknown>)
          : null;
      if (context && Object.keys(context).length > 0) {
        useChatState.getState().setPendingPageContext({ route, context });
      }
      window.location.hash = `#${route}`;
      return `ok: el usuario está ahora en ${route}${context ? " (contexto entregado a la página)" : ""}.`;
    },
    // Subtle in-thread chip so the hop is visible in the conversation too.
    render: ({ status }: { status?: string }) => (
      <GenericToolCard name="navigate_to" status={status} />
    ),
  });
}
