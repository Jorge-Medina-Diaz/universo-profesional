import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

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
        <QueryClientProvider client={client}>{children}</QueryClientProvider>
      </I18nextProvider>
    );
  };
}
