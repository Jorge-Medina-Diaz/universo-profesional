/**
 * Hash-based router — minimal, dependency-free, no external router needed.
 * Pages are matched by location.hash; auth-gated pages redirect to /login.
 */
import { useEffect, useState } from "react";
import { useAuthStore } from "@/shared/api";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { VerifyEmailPage } from "@/pages/VerifyEmailPage";
import { UniversePage } from "@/pages/UniversePage";
import { GenerateCvPage } from "@/pages/GenerateCvPage";
import { DocumentsPage } from "@/pages/DocumentsPage";
import { McpConnectPage } from "@/pages/McpConnectPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { BillingPage } from "@/pages/BillingPage";
import { OnboardingPage } from "@/pages/OnboardingPage";

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

  // Public routes
  if (path === "/login" || path === "/") {
    if (accessToken) {
      window.location.hash = "#/universe";
      return null;
    }
    return path === "/login" ? <LoginPage /> : <LandingPage />;
  }
  if (path === "/register") return accessToken ? redirect("/universe") : <RegisterPage />;
  if (path === "/auth/verify") return <VerifyEmailPage token={query.get("token") || ""} />;

  if (!accessToken) {
    window.location.hash = "#/login";
    return null;
  }

  // Authed routes
  if (path === "/onboarding") return <OnboardingPage />;
  if (path === "/universe") return <UniversePage />;
  if (path === "/cv/new") return <GenerateCvPage />;
  if (path === "/documents") return <DocumentsPage />;
  if (path === "/mcp") return <McpConnectPage />;
  if (path === "/settings") return <SettingsPage />;
  if (path === "/billing") return <BillingPage />;

  return <NotFoundPage path={path} />;
}

function redirect(p: string) {
  window.location.hash = `#${p}`;
  return null;
}

function LandingPage() {
  return (
    <div className="max-w-3xl mx-auto py-12 px-4 space-y-6">
      <h1 className="text-4xl font-bold tracking-tight">Universo Profesional</h1>
      <p className="text-lg text-gray-600">
        Sustituye el CV en Word por un universo profesional vivo. Genera CVs
        adaptados a cada oferta y conéctalo a Claude Code, Codex, Cursor y otros
        agentes de IA mediante MCP.
      </p>
      <div className="flex gap-3">
        <a href="#/register" className="btn-primary">Crear cuenta</a>
        <a href="#/login" className="btn-secondary">Iniciar sesión</a>
      </div>
      <div className="grid md:grid-cols-3 gap-4 mt-8">
        <Feature title="Universo persistente" body="Un grafo vivo de tu trayectoria, no un documento estático." />
        <Feature title="Generación adaptativa" body="Pegas una oferta y obtienes un CV optimizado en segundos." />
        <Feature title="MCP nativo" body="Habla con tu universo desde Claude Code, Codex, Cursor…" />
      </div>
    </div>
  );
}

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <div className="card">
      <h3 className="font-semibold mb-1">{title}</h3>
      <p className="text-sm text-gray-600">{body}</p>
    </div>
  );
}

function NotFoundPage({ path }: { path: string }) {
  return (
    <div className="max-w-md mx-auto py-12 px-4 text-center">
      <h1 className="text-2xl font-bold mb-2">404</h1>
      <p className="text-gray-600">Ruta no encontrada: {path}</p>
      <a href="#/" className="btn-primary mt-4">Inicio</a>
    </div>
  );
}
