/**
 * Hash-based router — minimal, dependency-free.
 * Pages are lazy-loaded so the initial bundle stays tiny — only the auth
 * shell + landing page ship in the main chunk.
 *
 * Every route is wrapped in its own ErrorBoundary so a crash in one page
 * does not kill the entire app.
 */
import { Suspense, lazy, useEffect, useState, type ComponentType } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore, universe } from "@/shared/api";
import { queryKeys } from "@/shared/queryKeys";
import { PageTransition } from "@/ui/motion";
import { PageSkeleton } from "@/ui";
import { ErrorBoundary } from "./ErrorBoundary";

// Public-facing lightweight pages stay eager — they're tiny and we want
// the first paint to be instant for landing/login.
import { LandingPage } from "@/pages/LandingPage";
import { LoginPage } from "@/pages/LoginPage";

const HomePage = lazyPage(() => import("@/pages/HomePage"), "HomePage");
const RegisterPage = lazyPage(() => import("@/pages/RegisterPage"), "RegisterPage");
const VerifyEmailPage = lazyPage(() => import("@/pages/VerifyEmailPage"), "VerifyEmailPage");
const UniversePage = lazyPage(() => import("@/pages/UniversePage"), "UniversePage");
const NotesPage = lazyPage(() => import("@/pages/NotesPage"), "NotesPage");
const GenerateCvPage = lazyPage(() => import("@/pages/GenerateCvPage"), "GenerateCvPage");
const DocumentsPage = lazyPage(() => import("@/pages/DocumentsPage"), "DocumentsPage");
const McpConnectPage = lazyPage(() => import("@/pages/McpConnectPage"), "McpConnectPage");
const SettingsPage = lazyPage(() => import("@/pages/SettingsPage"), "SettingsPage");
const BillingPage = lazyPage(() => import("@/pages/BillingPage"), "BillingPage");
const OnboardingPage = lazyPage(() => import("@/pages/OnboardingPage"), "OnboardingPage");
const ConnectionsPage = lazyPage(() => import("@/pages/ConnectionsPage"), "ConnectionsPage");
const OnboardingChatPage = lazyPage(
  () => import("@/pages/OnboardingChatPage"),
  "OnboardingChatPage",
);
const LinkedInCallbackPage = lazyPage(
  () => import("@/pages/LinkedInCallbackPage"),
  "LinkedInCallbackPage",
);
const ActivityPage = lazyPage(() => import("@/pages/ActivityPage"), "ActivityPage");
const SharePage = lazyPage(() => import("@/pages/SharePage"), "SharePage");
const CareerPreferencesPage = lazyPage(
  () => import("@/pages/CareerPreferencesPage"),
  "CareerPreferencesPage",
);
const JobsPage = lazyPage(() => import("@/pages/JobsPage"), "JobsPage");
const DocumentViewerPage = lazyPage(
  () => import("@/pages/DocumentViewerPage"),
  "DocumentViewerPage",
);
const CompareDocumentsPage = lazyPage(
  () => import("@/pages/CompareDocumentsPage"),
  "CompareDocumentsPage",
);
const LegalPage = lazyPage(() => import("@/pages/LegalPage"), "LegalPage");
const UsagePage = lazyPage(() => import("@/pages/UsagePage"), "UsagePage");

function parseHash(): { path: string; query: URLSearchParams } {
  const raw = (window.location.hash || "#/").slice(1);
  const [path, q = ""] = raw.split("?");
  return { path: path || "/", query: new URLSearchParams(q) };
}

export function Router() {
  const [route, setRoute] = useState(parseHash());
  const { accessToken } = useAuthStore();

  useEffect(() => {
    const onChange = () => setRoute(parseHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const { path, query } = route;

  // Onboarding gate: if the user is authenticated and has no universe data,
  // redirect them to the onboarding wizard (unless they're already there or
  // on a public/legal page).
  const summaryQuery = useQuery({
    queryKey: queryKeys.universe.summary,
    queryFn: () => universe.summary(),
    enabled: !!accessToken,
    staleTime: 5 * 60_000,
  });

  const isPublicOrOnboarding =
    path === "/onboarding" ||
    path === "/onboarding/chat" ||
    path.startsWith("/legal/") ||
    path.startsWith("/share/") ||
    path.startsWith("/auth/");

  const hasData = summaryQuery.data
    ? summaryQuery.data.counts.experiences > 0 ||
      summaryQuery.data.counts.educations > 0 ||
      summaryQuery.data.counts.skills > 0
    : true; // assume done while loading to avoid flashing redirect

  useEffect(() => {
    if (!accessToken) return;
    if (isPublicOrOnboarding) return;
    if (summaryQuery.isLoading) return;
    if (!hasData) {
      window.location.hash = "#/onboarding";
    }
  }, [accessToken, isPublicOrOnboarding, hasData, summaryQuery.isLoading]);

  const page = resolveRoute(path, query, !!accessToken);

  return (
    <PageTransition routeKey={path}>
      {/* Per-route ErrorBoundary: a crash in one page does not kill the app. */}
      <ErrorBoundary key={path}>
        <Suspense fallback={<RouteFallback />}>{page}</Suspense>
      </ErrorBoundary>
    </PageTransition>
  );
}

function resolveRoute(path: string, query: URLSearchParams, isAuthed: boolean) {
  // Public routes
  if (path === "/login" || path === "/") {
    if (isAuthed) {
      if (path === "/login") {
        return <Redirect to="/" />;
      }
      return <HomePage />;
    }
    return path === "/login" ? <LoginPage /> : <LandingPage />;
  }
  if (path === "/register") return isAuthed ? <Redirect to="/" /> : <RegisterPage />;
  if (path === "/auth/verify") return <VerifyEmailPage token={query.get("token") || ""} />;
  if (path === "/auth/linkedin/callback") return <LinkedInCallbackPage />;
  if (path.startsWith("/share/")) {
    const token = path.slice("/share/".length);
    return <SharePage token={token} />;
  }
  if (path.startsWith("/legal/")) {
    return <LegalPage doc={path.slice("/legal/".length)} />;
  }

  if (!isAuthed) {
    return <Redirect to="/login" />;
  }

  // Authed routes
  if (path === "/onboarding") return <OnboardingPage />;
  if (path === "/onboarding/chat") return <OnboardingChatPage />;
  if (path === "/connections") return <ConnectionsPage />;
  if (path === "/universe") return <UniversePage />;
  if (path === "/notes") return <NotesPage />;
  if (path === "/cv/new") return <GenerateCvPage />;
  if (path === "/documents") return <DocumentsPage />;
  if (path === "/mcp") return <McpConnectPage />;
  if (path === "/settings") return <SettingsPage />;
  if (path === "/billing") return <BillingPage />;
  if (path === "/usage") return <UsagePage />;
  if (path === "/activity") return <ActivityPage />;
  if (path === "/preferences") return <CareerPreferencesPage />;
  if (path === "/jobs") return <JobsPage />;
  if (path.startsWith("/documents/")) {
    const docId = path.slice("/documents/".length);
    return <DocumentViewerPage id={docId} />;
  }
  if (path === "/compare") {
    return (
      <CompareDocumentsPage
        initialA={query.get("a") ?? undefined}
        initialB={query.get("b") ?? undefined}
      />
    );
  }

  return <NotFoundPage path={path} />;
}

function Redirect({ to }: { to: string }) {
  useEffect(() => {
    window.location.hash = `#${to}`;
  }, [to]);
  return null;
}

function NotFoundPage({ path }: { path: string }) {
  return (
    <div className="max-w-md mx-auto py-24 px-4 text-center space-y-4">
      <h1 className="text-display font-medium leading-none text-ink">404</h1>
      <p className="text-stone">Ruta no encontrada: {path}</p>
      <a href="#/" className="btn-primary inline-flex">
        Volver al inicio
      </a>
    </div>
  );
}

/**
 * React.lazy() needs a default export. Pages historically use named exports,
 * so wrap them to keep the existing export style without per-page boilerplate.
 */
function lazyPage<P extends Record<string, unknown>, K extends keyof P>(
  loader: () => Promise<P>,
  name: K,
): P[K] {
  return lazy(async () => {
    const mod = await loader();
    return { default: mod[name] as ComponentType<unknown> };
  }) as unknown as P[K];
}

function RouteFallback() {
  return <PageSkeleton />;
}
