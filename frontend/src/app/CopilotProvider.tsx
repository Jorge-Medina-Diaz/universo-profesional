import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";
import { useAuthStore } from "@/shared/api";
import type { ReactNode } from "react";

/**
 * Wraps the app in CopilotKit. The runtime URL points at our self-hosted
 * `copilotkit-runtime` Node service. The MCP bearer (issued by our backend's
 * OAuth 2.1 server) is forwarded via `headers` — the runtime then passes it
 * to the MCP server it talks to.
 */
export function CopilotProvider({ children }: { children: ReactNode }) {
  const { accessToken } = useAuthStore();
  const runtimeUrl = (import.meta as any).env?.VITE_COPILOTKIT_RUNTIME_URL || "/copilotkit";
  return (
    <CopilotKit
      runtimeUrl={runtimeUrl}
      headers={accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined}
    >
      {children}
    </CopilotKit>
  );
}
