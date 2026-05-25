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
import { toast } from "@/ui";

/**
 * Structural shape of CopilotKit's error event (from `@copilotkit/shared`'s
 * `CopilotErrorEvent`). Typed locally to avoid importing a transitive package.
 */
type CopilotErrorLike = {
  type?: string;
  error?: { name?: string; message?: string } | unknown;
  context?: { source?: string };
};

let lastErrorToastAt = 0;

/**
 * Single observability hook for the agent runtime. CopilotKit logs every error
 * to the console itself; this handler decides what (if anything) the *user*
 * sees, and silences benign noise.
 *
 *  - Aborts ("BodyStreamBuffer was aborted" / AbortError) happen whenever the
 *    chat unmounts mid-stream — route change, React StrictMode's dev-only
 *    double-mount, or HMR. That's correct cancellation, never a user problem.
 *  - Connect/network failures (backend down, expired token) are otherwise
 *    silent — the composer just appears to do nothing. Surface a toast so the
 *    user knows to retry. Debounced because retries arrive in bursts.
 */
function handleCopilotError(event: CopilotErrorLike): void {
  if (event?.type !== "error") return;
  const err = event.error as { name?: string; message?: string } | undefined;
  const message = String(err?.message ?? err ?? "");
  if (err?.name === "AbortError" || /\babort(ed)?\b|BodyStreamBuffer/i.test(message)) {
    return;
  }
  const now = Date.now();
  if (now - lastErrorToastAt < 6000) return;
  lastErrorToastAt = now;
  const isConnect =
    event.context?.source === "network" ||
    /failed to fetch|network ?error|load failed|connect/i.test(message);
  if (isConnect) {
    toast.error(
      "No pude conectar con tu agente",
      "Comprueba tu conexión o que el servidor esté activo, e inténtalo de nuevo.",
    );
  } else {
    toast.error("El agente tuvo un problema", message.slice(0, 160) || undefined);
  }
}

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
  headers?: Record<string, string> | (() => Record<string, string>);
  showDevConsole?: boolean;
  enableInspector?: boolean;
  onError?: (event: CopilotErrorLike) => void;
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
  const [enabled, setEnabled] = useState(false);
  const [mod, setMod] = useState<CopilotKitModule | null>(null);

  // CopilotKit bypasses the REST client, so it can't reuse its 401→refresh
  // retry. A header *function* (re-invoked per request) reads the latest token
  // from the store at request time, so the chat always sends a fresh
  // Authorization header — including right after the REST layer silently
  // rotates an expired token.
  const authHeaders = useCallback((): Record<string, string> => {
    const token = useAuthStore.getState().accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, []);

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
        showDevConsole={false}
        enableInspector={false}
        onError={handleCopilotError}
        headers={authHeaders}
      >
        {children}
      </CopilotKit>
    </CopilotErrorBoundary>
  );
}
