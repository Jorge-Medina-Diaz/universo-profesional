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
import { useAuthStore, universe, auth } from "@/shared/api";
import { queryKeys } from "@/shared/queryKeys";
import { isOnboardingComplete, hasUniverseData } from "@/shared/onboarding";
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
const ForgotPasswordPage = lazyPage(() => import("@/pages/ResetPasswordPage"), "ForgotPasswordPage");
const ResetPasswordPage = lazyPage(() => import("@/pages/ResetPasswordPage"), "ResetPasswordPage");
const UniversePage = lazyPage(() => import("@/pages/UniversePage"), "UniversePage");
const NotesPage = lazyPage(() => import("@/pages/NotesPage"), "NotesPage");
const GenerateCvPage = lazyPage(() => import("@/pages/GenerateCvPage"), "GenerateCvPage");
const DocumentsPage = lazyPage(() => import("@/pages/DocumentsPage"), "DocumentsPage");
const McpConnectPage = lazyPage(() => import("@/pages/McpConnectPage"), "McpConnectPage");
const SettingsPage = lazyPage(() => import("@/pages/SettingsPage"), "SettingsPage");
const BillingPage = lazyPage(() => import("@/pages/BillingPage"), "BillingPage");
const CheckoutMockPage = lazyPage(() => import("@/pages/CheckoutMockPage"), "CheckoutMockPage");
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
const PublicTwinPage = lazyPage(() => import("@/pages/PublicTwinPage"), "PublicTwinPage");
const TwinSettingsPage = lazyPage(() => import("@/pages/TwinSettingsPage"), "TwinSettingsPage");
const CareerPreferencesPage = lazyPage(
  () => import("@/pages/CareerPreferencesPage"),
  "CareerPreferencesPage",
);
const JobsPage = lazyPage(() => import("@/pages/JobsPage"), "JobsPage");
const InterviewPrepPage = lazyPage(
  () => import("@/pages/InterviewPrepPage"),
  "InterviewPrepPage",
);
const RemindersPage = lazyPage(() => import("@/pages/RemindersPage"), "RemindersPage");
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
  const rawHash = window.location.hash || "#/";
  // This is a hash router, so a route always looks like "#/...". Anything else
  // (e.g. "#producto", "#main") is an in-page anchor on the current page — NOT
  // a route. Treating it as one sent the landing's section links through
  // resolveRoute(), which bounced every unauthenticated visitor to /login.
  // Resolve anchors to the root path and let the browser handle the scroll.
  if (!rawHash.startsWith("#/")) {
    return { path: "/", query: new URLSearchParams() };
  }
  const raw = rawHash.slice(1);
  const [path, q = ""] = raw.split("?");
  return { path: path || "/", query: new URLSearchParams(q) };
}

export function Router() {
  const [route, setRoute] = useState(parseHash());
  const { accessToken, userId } = useAuthStore();

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

  // Server-side onboarding state (cross-device); shares the cache Layout warms.
  const meQuery = useQuery({
    queryKey: queryKeys.me.all,
    queryFn: () => auth.me(),
    enabled: !!accessToken,
    staleTime: 5 * 60_000,
  });

  const isPublicOrOnboarding =
    path === "/onboarding" ||
    path === "/onboarding/chat" ||
    path.startsWith("/legal/") ||
    path.startsWith("/share/") ||
    path.startsWith("/t/") ||
    path.startsWith("/auth/");

  // Assume "has data" until the query actually SUCCEEDS, so neither a loading
  // nor an errored summary fires a spurious redirect.
  const hasData = summaryQuery.isSuccess
    ? hasUniverseData(summaryQuery.data)
    : true;

  useEffect(() => {
    if (!accessToken) return;
    if (isPublicOrOnboarding) return;
    // Gate on SUCCESS (not just !isLoading): an errored query also has
    // isLoading=false, and we must never bounce a user on a transient summary
    // failure. Both queries must have resolved successfully.
    if (!summaryQuery.isSuccess || !meQuery.isSuccess) return;
    // Only funnel users who still have an empty universe AND haven't already
    // been through onboarding. Without the second check the gate bounces a
    // user who just finished/skipped onboarding (and added nothing) straight
    // back from /universe — making the "Ir a mi universo" button look broken.
    if (
      !hasData &&
      !isOnboardingComplete(userId, meQuery.data?.onboarding_completed_at)
    ) {
      window.location.hash = "#/onboarding/chat";
    }
  }, [
    accessToken,
    userId,
    isPublicOrOnboarding,
    hasData,
    summaryQuery.isSuccess,
    meQuery.isSuccess,
    meQuery.data?.onboarding_completed_at,
  ]);

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
  if (path === "/auth/forgot") return <ForgotPasswordPage />;
  if (path === "/auth/reset") return <ResetPasswordPage token={query.get("token") || ""} />;
  if (path === "/auth/linkedin/callback") return <LinkedInCallbackPage />;
  if (path.startsWith("/share/")) {
    const token = path.slice("/share/".length);
    return <SharePage token={token} />;
  }
  if (path.startsWith("/t/")) {
    const slug = path.slice("/t/".length);
    return <PublicTwinPage slug={slug} embed={query.get("embed") === "1"} />;
  }
  if (path.startsWith("/legal/")) {
    return <LegalPage doc={path.slice("/legal/".length)} />;
  }

  if (!isAuthed) {
    return <Redirect to="/login" />;
  }

  // Authed routes
  // The form-wizard onboarding was retired in favour of the agentic chat flow;
  // keep the old path as a redirect so any bookmarks / in-app links still land.
  if (path === "/onboarding") return <Redirect to="/onboarding/chat" />;
  if (path === "/onboarding/chat") return <OnboardingChatPage />;
  if (path === "/connections") return <ConnectionsPage />;
  if (path === "/universe") return <UniversePage />;
  if (path === "/notes") return <NotesPage />;
  if (path === "/cv/new") return <GenerateCvPage />;
  if (path === "/documents") return <DocumentsPage />;
  if (path === "/mcp") return <McpConnectPage />;
  if (path === "/settings") return <SettingsPage />;
  if (path === "/billing") return <BillingPage />;
  if (path === "/billing/checkout-mock") return <CheckoutMockPage />;
  if (path === "/usage") return <UsagePage />;
  if (path === "/activity") return <ActivityPage />;
  if (path === "/preferences") return <CareerPreferencesPage />;
  if (path === "/jobs") return <JobsPage />;
  if (path.startsWith("/jobs/") && path.endsWith("/prep")) {
    const jobId = path.slice("/jobs/".length, -"/prep".length);
    return <InterviewPrepPage jobId={jobId} />;
  }
  if (path === "/reminders") return <RemindersPage />;
  if (path === "/twin") return <TwinSettingsPage />;
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
