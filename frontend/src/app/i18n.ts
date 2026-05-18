import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

const resources = {
  es: {
    translation: {
      app: {
        title: "Universo Profesional",
        tagline: "Tu universo profesional, vivo y al servicio de tu carrera",
      },
      auth: {
        login: "Iniciar sesión",
        register: "Crear cuenta",
        logout: "Salir",
        email: "Email",
        password: "Contraseña",
        forgot: "He olvidado mi contraseña",
        verify: "Verificar email",
        verifyHint: "Te hemos enviado un email para verificar tu cuenta. Revisa Mailhog: http://localhost:8025",
        loginCta: "Entrar",
        registerCta: "Registrarme",
        noAccount: "¿No tienes cuenta?",
        haveAccount: "¿Ya tienes cuenta?",
      },
      universe: {
        title: "Mi Universo",
        summary: "Resumen",
        education: "Educación",
        experience: "Experiencia",
        skills: "Competencias",
        projects: "Proyectos",
        certifications: "Certificaciones",
        languages: "Idiomas",
        preferences: "Preferencias",
        empty: "Empieza añadiendo entradas a tu universo.",
        add: "Añadir",
      },
      cv: {
        generate: "Generar CV",
        jobUrl: "URL de la oferta",
        jobDescription: "Descripción del puesto",
        templateAtsClassic: "ATS clásica",
        languageEs: "Español",
        languageEn: "Inglés",
        toneProfessional: "Profesional",
        toneConversational: "Conversacional",
        downloadPdf: "Descargar PDF",
        downloadDocx: "Descargar DOCX",
        downloadJson: "Descargar JSON",
      },
      mcp: {
        title: "Conecta tu agente de IA",
        intro: "Accede a tu universo profesional desde Claude Code, Codex, Cursor y más.",
        endpoint: "Endpoint MCP",
      },
      billing: {
        title: "Suscripción",
        free: "Free",
        premium: "Premium",
        pro: "Pro",
        upgrade: "Mejorar plan",
        cancel: "Cancelar suscripción",
      },
      settings: {
        title: "Ajustes",
        exportRgpd: "Descargar mis datos (RGPD)",
        deleteAccount: "Eliminar cuenta",
        deleteConfirm: "Confirma eliminando tu cuenta. Se aplicará un borrado físico tras 30 días.",
      },
      common: {
        save: "Guardar",
        cancel: "Cancelar",
        delete: "Borrar",
        edit: "Editar",
        loading: "Cargando…",
        error: "Algo ha salido mal",
      },
    },
  },
  en: {
    translation: {
      app: { title: "Professional Universe", tagline: "Your professional universe, alive and at your career's service" },
      auth: {
        login: "Sign in", register: "Create account", logout: "Sign out",
        email: "Email", password: "Password",
        forgot: "Forgot password?", verify: "Verify email",
        verifyHint: "We've sent you a verification email. In dev, check Mailhog: http://localhost:8025",
        loginCta: "Sign in", registerCta: "Sign up",
        noAccount: "No account yet?", haveAccount: "Already have an account?",
      },
      universe: {
        title: "My Universe", summary: "Summary",
        education: "Education", experience: "Experience", skills: "Skills",
        projects: "Projects", certifications: "Certifications", languages: "Languages",
        preferences: "Preferences", empty: "Start by adding entries to your universe.", add: "Add",
      },
      cv: {
        generate: "Generate CV", jobUrl: "Job URL", jobDescription: "Job description",
        templateAtsClassic: "ATS Classic", languageEs: "Spanish", languageEn: "English",
        toneProfessional: "Professional", toneConversational: "Conversational",
        downloadPdf: "Download PDF", downloadDocx: "Download DOCX", downloadJson: "Download JSON",
      },
      mcp: {
        title: "Connect your AI agent",
        intro: "Access your professional universe from Claude Code, Codex, Cursor and more.",
        endpoint: "MCP endpoint",
      },
      billing: { title: "Subscription", free: "Free", premium: "Premium", pro: "Pro", upgrade: "Upgrade", cancel: "Cancel" },
      settings: {
        title: "Settings", exportRgpd: "Download my data (GDPR)",
        deleteAccount: "Delete account",
        deleteConfirm: "Confirm by deleting your account. Hard delete after 30 days.",
      },
      common: { save: "Save", cancel: "Cancel", delete: "Delete", edit: "Edit", loading: "Loading…", error: "Something went wrong" },
    },
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "es",
    interpolation: { escapeValue: false },
  });

export default i18n;
