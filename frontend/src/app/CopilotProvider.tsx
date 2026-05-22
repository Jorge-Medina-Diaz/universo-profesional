/**
 * CopilotKit wrapper with lazy loading.
 *
 * The library is ~3 MB minified — by far the heaviest dep. Most pages don't
 * use the chat, so we only fetch CopilotKit when a chat surface explicitly
 * asks for it via `enableCopilot()`. Until then the provider is a pass-through
 * and the chunk stays out of the initial download.
 */
import {
  Component,
  useCallback,
  useEffect,
  useState,
  useSyncExternalStore,
  type ComponentType,
  type ErrorInfo,
  type ReactNode,
} from "react";
import { useAuthStore } from "@/shared/api";

const readyListeners = new Set<() => void>();
let copilotReady = false;
function setCopilotReady() {
  copilotReady = true;
  readyListeners.forEach((fn) => fn());
}
function subscribeReady(cb: () => void) {
  readyListeners.add(cb);
  return () => {
    readyListeners.delete(cb);
  };
}

/** Returns true once CopilotKit's bundle has finished loading. */
export function useCopilotReady(): boolean {
  return useSyncExternalStore(
    subscribeReady,
    () => copilotReady,
    () => false,
  );
}

class CopilotErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
     
    console.warn(
      "[copilotkit] disabled after runtime error — chat features unavailable",
      error,
      info,
    );
  }

  render() {
    if (this.state.failed) return this.props.children;
    return this.props.children;
  }
}

type CopilotKitModule = typeof import("@copilotkit/react-core");
type CopilotKitComponent = ComponentType<{
  runtimeUrl: string;
  agent: string;
  headers?: Record<string, string>;
  children: ReactNode;
}>;

let externalEnable: (() => void) | null = null;

/**
 * Call from chat surfaces (HomePage, OnboardingChatPage) on mount. Triggers
 * dynamic import of CopilotKit. Idempotent.
 */
export function enableCopilot() {
  externalEnable?.();
}

export function CopilotProvider({ children }: { children: ReactNode }) {
  const { accessToken } = useAuthStore();
  const [enabled, setEnabled] = useState(false);
  const [mod, setMod] = useState<CopilotKitModule | null>(null);

  const enable = useCallback(() => {
    if (enabled) return;
    setEnabled(true);
    void Promise.all([
      import("@copilotkit/react-core"),
      // CSS bundled with react-ui. Cast through `as string` to satisfy TS
      // (there's no module declaration for the .css export).
      import("@copilotkit/react-ui/styles.css" as never),
    ]).then(([core]) => {
      setMod(core);
      setCopilotReady();
    });
  }, [enabled]);

  useEffect(() => {
    externalEnable = enable;
    return () => {
      if (externalEnable === enable) externalEnable = null;
    };
  }, [enable]);

  if (!mod) {
    // Either not enabled yet, or enabled but not loaded — render children
    // directly. Chat-using components show a spinner via Suspense or local
    // state; everything else renders normally.
    return <CopilotErrorBoundary>{children}</CopilotErrorBoundary>;
  }

  const CopilotKit = mod.CopilotKit as CopilotKitComponent;
  const env = (import.meta as never as { env: Record<string, string | undefined> }).env || {};
  const apiBase = env.VITE_API_BASE_URL || "";
  const runtimeUrl = env.VITE_AGUI_URL || `${apiBase}/agui`;

  return (
    <CopilotErrorBoundary>
      <CopilotKit
        runtimeUrl={runtimeUrl}
        agent="universe_coordinator"
        headers={accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined}
      >
        {children}
      </CopilotKit>
    </CopilotErrorBoundary>
  );
}
