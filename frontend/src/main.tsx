import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@fontsource/dm-sans/400.css";
import "@fontsource/dm-sans/500.css";
import { App } from "./app/App";
import "./app/i18n";
import "./styles/index.css";
import { initSentry } from "./shared/sentry";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
  },
});

// Fire-and-forget Sentry init — no-op if VITE_SENTRY_DSN is unset or the
// user hasn't accepted the analytics consent yet. The cookie banner calls
// `initSentry()` again on opt-in (idempotent).
void initSentry();

const root = document.getElementById("root");
if (!root) throw new Error("#root not found");

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
