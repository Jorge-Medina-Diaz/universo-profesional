/**
 * Console error policy — enforces the "no silent errors" rule (see the
 * `no-silent-errors` memory) at the most reliable choke point we have.
 *
 * Why the console: CopilotKit does NOT reliably invoke the `<CopilotKit onError>`
 * prop for backend run failures in v1.7 — but it DOES always `console.error` them
 * (`[CopilotKit] Agent error: …`, `[CopilotKit] sendMessage error: …`). So we
 * patch `console.error` to:
 *
 *   1. DROP the one benign signature — "BodyStreamBuffer was aborted" / AbortError
 *      from a cancelled run (unmount / StrictMode double-mount / HMR / Stop). A
 *      cancellation is not an error.
 *   2. SURFACE every genuine CopilotKit/agent error to the user as a toast
 *      (deduped), so a failed chat turn is never silent.
 *   3. Pass everything through to the real console untouched.
 *
 * `surfaceAgentError` is also exported so the `onError` prop can route through the
 * same deduped path as a belt-and-suspenders backup.
 *
 * Imported for its side effect as the very first line of `main.tsx`.
 */

const ABORT_SIGNATURE = /BodyStreamBuffer was aborted/;
const COPILOT_ABORT = /\[CopilotKit\][\s\S]*\bAbortError\b/;
const COPILOT_ERROR =
  /\[CopilotKit\][\s\S]*(agent error|sendmessage error|agent_connect_failed|agent_run_failed|agent_run_error|run[_ ]?error|not found|failed to load runtime info|runtime info|error \()/i;

let lastAgentErrorAt = 0;

function argsToText(args: unknown[]): string {
  return args
    .map((a) => {
      if (typeof a === "string") return a;
      if (a && typeof a === "object") {
        const e = a as { message?: unknown; name?: unknown };
        return `${String(e.name ?? "")} ${String(e.message ?? "")}`;
      }
      return "";
    })
    .join(" ");
}

function cleanMessage(raw: string): string {
  return raw
    .replace(/^\[CopilotKit\][^:]*:\s*/i, "")
    .replace(/\s+Code:[\s\S]*$/i, "")
    .replace(/\s+at\s+[\s\S]*$/i, "")
    .trim();
}

/** DOM event name the in-app listener ({@link AgentErrorListener}) handles. */
export const AGENT_ERROR_EVENT = "cvs:agent-error";

/**
 * Surface an agent/runtime failure to the user. Deduped (4s) so the two console
 * lines CopilotKit emits per failure (and the onError backup) yield one toast.
 *
 * We DON'T call `toast` here: this module is imported first (before React), and
 * a dynamic `import("@/ui")` from this early context resolves to a *second*
 * module instance whose toaster singleton is never registered (so the toast
 * silently no-ops). Instead we dispatch a DOM event that a normal in-app
 * component — using the real, registered toaster — renders. Decoupled and
 * immune to module-instance mismatches.
 */
export function surfaceAgentError(rawMessage: string): void {
  const now = Date.now();
  if (now - lastAgentErrorAt < 4000) return;
  lastAgentErrorAt = now;

  const lower = (rawMessage || "").toLowerCase();
  let title = "El agente tuvo un problema";
  let description =
    cleanMessage(rawMessage).slice(0, 200) ||
    "Fallo del agente. Revisa los logs del servidor.";

  if (
    /credit balance|insufficient|quota|rate.?limit|\b429\b|billing|overloaded|sin crédito|no está disponible|no devolvió/.test(
      lower,
    )
  ) {
    title = "El agente no está disponible ahora";
    description =
      "El servicio de IA se quedó sin crédito o superó su límite. Inténtalo de nuevo en un rato.";
  } else if (
    /failed to fetch|network ?error|networkerror|load failed|connect|econn|timeout/.test(
      lower,
    )
  ) {
    title = "No pude conectar con tu agente";
    description =
      "Comprueba tu conexión o que el servidor esté activo, e inténtalo de nuevo.";
  }

  try {
    window.dispatchEvent(
      new CustomEvent(AGENT_ERROR_EVENT, { detail: { title, description } }),
    );
  } catch {
    /* no DOM (SSR/tests) — nothing to surface */
  }
}

const originalConsoleError = console.error.bind(console);
console.error = (...args: unknown[]) => {
  const text = argsToText(args);
  // 1. Benign cancellation — drop entirely.
  if (ABORT_SIGNATURE.test(text) || COPILOT_ABORT.test(text)) return;
  // 2. Genuine agent/runtime error — surface to the user.
  if (COPILOT_ERROR.test(text)) {
    try {
      surfaceAgentError(text);
    } catch {
      /* never let surfacing break logging */
    }
  }
  // 3. Always log the real error.
  originalConsoleError(...args);
};

export {};
