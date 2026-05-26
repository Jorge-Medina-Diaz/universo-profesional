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
import { AGENT_ERROR_EVENT, surfaceAgentError } from "./silenceBenignErrors";

/**
 * Structural shape of CopilotKit's error event (from `@copilotkit/shared`'s
 * `CopilotErrorEvent`). Typed locally to avoid importing a transitive package.
 */
type CopilotErrorLike = {
  type?: string;
  error?: { name?: string; message?: string } | string | unknown;
  message?: string;
  context?: { source?: string };
};

/**
 * Backup observability hook for the agent runtime. The primary, reliable path
 * is the `console.error` patch in `silenceBenignErrors` (CopilotKit always logs
 * failures there); this `onError` prop is unreliable in v1.7 but kept as a
 * second detector. Both funnel into the same deduped `surfaceAgentError`, so a
 * single failure yields exactly one toast and is NEVER silent
 * (see [[no-silent-errors]]). Pure cancellation (AbortError) is ignored.
 */
function handleCopilotError(event: CopilotErrorLike): void {
  const rawErr = event?.error;
  const errObj =
    rawErr && typeof rawErr === "object"
      ? (rawErr as { name?: string; message?: string })
      : undefined;
  const message = String(
    errObj?.message ?? (typeof rawErr === "string" ? rawErr : "") ?? event?.message ?? "",
  );

  // Benign cancellation — not an error.
  if (errObj?.name === "AbortError" || /\babort(ed)?\b|BodyStreamBuffer/i.test(message)) {
    return;
  }
  // Skip pure observability ticks (request/response/performance) with no error.
  if (!rawErr && event?.type !== "error") return;

  surfaceAgentError(message || "El agente tuvo un problema.");
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
    if (this.state.failed) {
      return (
        <div className="flex flex-col items-center justify-center gap-3 p-6 text-center">
          <div className="rounded-card border border-red-200 bg-red-50/60 px-4 py-3 max-w-sm">
            <p className="text-sm font-medium text-red-800">El chat no está disponible</p>
            <p className="mt-0.5 text-xs text-red-700/90">
              Algo salió mal al cargar el agente. Puedes seguir usando el resto de la app.
            </p>
          </div>
          <button
            type="button"
            onClick={() => this.setState({ failed: false })}
            className="text-xs text-ink underline-offset-2 hover:underline"
          >
            Reintentar
          </button>
        </div>
      );
    }
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
    void import("@copilotkit/react-core").then((core) => {
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

  // Render agent/runtime failures surfaced by `surfaceAgentError` (from the
  // console patch or the onError backup) as a toast, using the real registered
  // toaster. Decoupled via a DOM event so the early-loaded error module never
  // touches a stray toaster instance — guarantees no silent agent error.
  useEffect(() => {
    const onAgentError = (e: Event) => {
      const detail = (e as CustomEvent).detail as
        | { title?: string; description?: string }
        | undefined;
      toast.error(detail?.title || "El agente tuvo un problema", detail?.description);
    };
    window.addEventListener(AGENT_ERROR_EVENT, onAgentError);
    return () => window.removeEventListener(AGENT_ERROR_EVENT, onAgentError);
  }, []);

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
