import { render, type RenderResult } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import type { GraphSnapshot } from "@/graph/api";
import { ToasterProvider } from "@/ui";

i18n.use(initReactI18next).init({
  lng: "es",
  fallbackLng: "es",
  interpolation: { escapeValue: false },
  resources: {
    es: {
      translation: {
        auth: {
          email: "Email",
          password: "Contraseña",
          login: "Iniciar sesión",
          loginCta: "Entrar",
          register: "Crear cuenta",
          registerCta: "Crear cuenta",
          verify: "Verifica tu email",
          verifyHint: "Te hemos enviado un enlace de verificación.",
          haveAccount: "¿Ya tienes cuenta?",
          noAccount: "¿No tienes cuenta?",
        },
        common: { loading: "Cargando..." },
      },
    },
  },
});

export function createTestWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <I18nextProvider i18n={i18n}>
        <QueryClientProvider client={client}>
          <ToasterProvider>{children}</ToasterProvider>
        </QueryClientProvider>
      </I18nextProvider>
    );
  };
}

export function renderWithProviders(ui: React.ReactElement): RenderResult & { client: QueryClient } {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={client}>
        <ToasterProvider>{children}</ToasterProvider>
      </QueryClientProvider>
    </I18nextProvider>
  );
  return { ...render(ui, { wrapper: Wrapper }), client } as RenderResult & { client: QueryClient };
}

export function mockGraphSnapshot(): GraphSnapshot {
  return {
    nodes: [
      {
        key: "skill-1",
        attributes: {
          kind: "skill",
          label: "Python",
          area: "backend",
          esco_uri: "http://data.europa.eu/esco/skill/123",
        },
      },
      {
        key: "exp-1",
        attributes: {
          kind: "experience",
          label: "Senior Dev at Acme",
          area: "backend",
        },
      },
      {
        key: "proj-1",
        attributes: {
          kind: "project",
          label: "OpenSource CLI",
          area: "frontend",
        },
      },
      {
        key: "edu-1",
        attributes: {
          kind: "education",
          label: "CS Degree",
          area: "data",
        },
      },
    ],
    edges: [
      {
        key: "e1",
        source: "exp-1",
        target: "skill-1",
        attributes: { edge_type: "uses", confidence: 0.9 },
      },
      {
        key: "e2",
        source: "proj-1",
        target: "skill-1",
        attributes: { edge_type: "uses", confidence: 0.7 },
      },
    ],
    node_count: 4,
    edge_count: 2,
  };
}
