/**
 * Suppress CopilotKit's benign stream-abort console noise.
 *
 * CopilotKit hardcodes `console.error("[CopilotKit] … BodyStreamBuffer was
 * aborted", AbortError)` whenever an in-flight agent run is *cancelled* — which
 * happens constantly and correctly: route changes, React StrictMode's dev-only
 * double-mount, Vite HMR, or the user pressing the Stop button. Each of the
 * ~5 `useCopilotChat()` consumers opens its own coagent connection, so a single
 * dev reload prints a dozen identical abort lines that bury real errors.
 *
 * A cancelled request is never an actionable error, so we drop *only* this exact
 * signature and pass everything else through untouched — 401s, "Failed to
 * fetch", and any other CopilotKit error still reach the console. The `onError`
 * prop on <CopilotKit> can't do this (it's an extra observability hook, not a
 * replacement for the library's internal logging), so we filter at the console.
 *
 * Imported for its side effect as the very first line of `main.tsx` so the
 * patch is installed before React (or the lazily-loaded CopilotKit) can log.
 */
const ABORT_SIGNATURE = /BodyStreamBuffer was aborted/;
const COPILOT_ABORT = /\[CopilotKit\][\s\S]*\bAbortError\b/;

function isBenignAbort(args: unknown[]): boolean {
  const text = args
    .map((a) => {
      if (typeof a === "string") return a;
      if (a && typeof a === "object") {
        const e = a as { message?: unknown; name?: unknown };
        return `${String(e.name ?? "")} ${String(e.message ?? "")}`;
      }
      return "";
    })
    .join(" ");
  return ABORT_SIGNATURE.test(text) || COPILOT_ABORT.test(text);
}

const originalConsoleError = console.error.bind(console);
console.error = (...args: unknown[]) => {
  if (isBenignAbort(args)) return;
  originalConsoleError(...args);
};

export {};
