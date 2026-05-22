/**
 * Sentry browser SDK — lazy-loaded so the bundle only pays the cost when
 * a `VITE_SENTRY_DSN` is configured. Otherwise it's a no-op.
 *
 * PII safety:
 *   - `sendDefaultPii: false`
 *   - `beforeSend` strips Authorization headers + token-shaped strings.
 *
 * Cookie-consent gating: we DON'T initialize Sentry until the user
 * accepts (or has previously accepted) the "analytics/diagnostics" consent
 * bucket. See `CookieConsentBanner.tsx`. If the consent is missing,
 * `initSentry()` is a no-op and the bundle stays unloaded.
 */

const JWT_RE = /eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g;
const STRIPE_KEY_RE = /sk_(live|test)_[A-Za-z0-9]+/g;

let initialized = false;

export async function initSentry(): Promise<void> {
  if (initialized) return;
  const dsn = (import.meta.env.VITE_SENTRY_DSN as string | undefined)?.trim();
  if (!dsn) return;

  // Respect cookie consent. We check synchronously so the dynamic import
  // below only runs when consent is granted.
  try {
    const raw = localStorage.getItem("cvs-saas-cookie-consent");
    if (raw) {
      const parsed = JSON.parse(raw) as { analytics?: boolean };
      if (parsed.analytics === false) return;
    } else {
      // No decision yet — wait until the user opts in. The consent banner
      // calls `initSentry()` itself when the user accepts.
      return;
    }
  } catch {
    return;
  }

  initialized = true;
  const Sentry = await import("@sentry/react");
  Sentry.init({
    dsn,
    environment: (import.meta.env.MODE as string) || "production",
    sendDefaultPii: false,
    tracesSampleRate: 0.1,
    integrations: [
      Sentry.browserTracingIntegration(),
    ],
    beforeSend(event: import("@sentry/react").ErrorEvent) {
      // Scrub headers + obvious tokens.
      if (event.request?.headers) {
        const h = event.request.headers as Record<string, string>;
        for (const k of Object.keys(h)) {
          if (/^(authorization|cookie|x-api-key)$/i.test(k)) h[k] = "[redacted]";
        }
      }
      const walk = (node: unknown): unknown => {
        if (typeof node === "string")
          return node.replace(JWT_RE, "<jwt>").replace(STRIPE_KEY_RE, "<stripe-key>");
        if (Array.isArray(node)) return node.map(walk);
        if (node && typeof node === "object") {
          const out: Record<string, unknown> = {};
          for (const [k, v] of Object.entries(node as Record<string, unknown>)) {
            out[k] = walk(v);
          }
          return out;
        }
        return node;
      };
      return walk(event) as typeof event;
    },
  });
}

export async function captureError(error: unknown): Promise<void> {
  if (!initialized) return;
  const Sentry = await import("@sentry/react");
  Sentry.captureException(error);
}
