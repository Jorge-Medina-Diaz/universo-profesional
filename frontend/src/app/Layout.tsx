import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/shared/api";
import type { ReactNode } from "react";

interface Props {
  title: string;
  isAuthed: boolean;
  children: ReactNode;
}

export function Layout({ title, isAuthed, children }: Props) {
  const { t, i18n } = useTranslation();
  const { clear, email } = useAuthStore();

  const logout = () => {
    clear();
    window.location.hash = "#/login";
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-gray-200 bg-white">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <a href="#/" className="flex items-center gap-2 font-semibold">
            <span aria-hidden className="inline-block w-2 h-2 rounded-full bg-brand-500" />
            {title}
          </a>
          <nav className="hidden md:flex gap-3 text-sm items-center">
            {isAuthed ? (
              <>
                <NavLink href="#/universe">{t("universe.title")}</NavLink>
                <NavLink href="#/connections">Conexiones</NavLink>
                <NavLink href="#/cv/new">{t("cv.generate")}</NavLink>
                <NavLink href="#/documents">Documentos</NavLink>
                <NavLink href="#/mcp">MCP</NavLink>
                <NavLink href="#/billing">{t("billing.title")}</NavLink>
                <NavLink href="#/settings">{t("settings.title")}</NavLink>
                <span className="text-gray-500 text-xs">{email}</span>
                <button onClick={logout} className="btn-secondary">{t("auth.logout")}</button>
              </>
            ) : (
              <>
                <NavLink href="#/login">{t("auth.login")}</NavLink>
                <NavLink href="#/register">{t("auth.register")}</NavLink>
              </>
            )}
            <select
              value={i18n.resolvedLanguage}
              onChange={(e) => i18n.changeLanguage(e.target.value)}
              aria-label="Language"
              className="text-xs border rounded p-1"
            >
              <option value="es">ES</option>
              <option value="en">EN</option>
            </select>
          </nav>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t border-gray-200 bg-white py-4 mt-8">
        <div className="max-w-6xl mx-auto px-4 text-xs text-gray-500 flex flex-wrap gap-3 justify-between">
          <span>© {new Date().getFullYear()} Universo Profesional · MVP local</span>
          <span className="flex gap-3">
            <a href="#/legal/terms">Términos</a>
            <a href="#/legal/privacy">Privacidad</a>
            <a href="#/legal/cookies">Cookies</a>
          </span>
        </div>
      </footer>
    </div>
  );
}

function NavLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} className="text-gray-700 hover:text-gray-900">
      {children}
    </a>
  );
}
