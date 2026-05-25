// Side-effect import — must run first to install the console filter before
// React or the lazily-loaded CopilotKit can emit their benign abort noise.
import "./app/silenceBenignErrors";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@fontsource/dm-sans/400.css";
import "@fontsource/dm-sans/500.css";
// Editorial display face — Fraunces (variable: optical sizing + weight) is
// paired with DM Sans for body. Used for hero/display headings + section
// numbers to give the product a distinctive editorial voice.
import "@fontsource-variable/fraunces";
import { App } from "./app/App";
import "./app/i18n";
import "./styles/index.css";
import { initSentry } from "./shared/sentry";
import { startTokenAutoRefresh } from "./shared/api";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
  },
});

// Fire-and-forget Sentry init — no-op if VITE_SENTRY_DSN is unset or the
// user hasn't accepted the analytics consent yet. The cookie banner calls
// `initSentry()` again on opt-in (idempotent).
void initSentry();

// Keep the access token fresh on long/idle sessions so the chat and API calls
// never hit the brief 401-then-recover flash. Idempotent.
startTokenAutoRefresh();

const root = document.getElementById("root");
if (!root) throw new Error("#root not found");

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
