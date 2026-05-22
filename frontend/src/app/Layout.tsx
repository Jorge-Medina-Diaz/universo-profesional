import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/shared/api";
import { useHashRoute } from "@/shared/useHashRoute";
import { Search } from "lucide-react";
import type { ReactNode } from "react";
import { Button, cn } from "@/ui";
import { BottomNav } from "./BottomNav";
import { openCommandPalette } from "./CommandPalette";
import { NotificationCenter } from "@/widgets/NotificationCenter";
import { CookieConsentBanner } from "@/widgets/CookieConsentBanner";
import { CompletenessPill } from "@/widgets/ProfileCompleteness";
import { ThemeToggle } from "./ThemeToggle";

interface Props {
  title: string;
  isAuthed: boolean;
  children: ReactNode;
}

const NAV_ITEMS: Array<{ href: string; label: () => string; match: (p: string) => boolean }> = [
  { href: "#/", label: () => "Chat", match: (p) => p === "/" },
  { href: "#/universe", label: () => "Universo", match: (p) => p.startsWith("/universe") },
  { href: "#/connections", label: () => "Conexiones", match: (p) => p.startsWith("/connections") },
  { href: "#/cv/new", label: () => "Generar CV", match: (p) => p.startsWith("/cv") },
  { href: "#/documents", label: () => "Documentos", match: (p) => p.startsWith("/documents") },
  { href: "#/mcp", label: () => "MCP", match: (p) => p.startsWith("/mcp") },
];

export function Layout({ title, isAuthed, children }: Props) {
  const { i18n } = useTranslation();
  const { clear, email } = useAuthStore();
  const path = useHashRoute();

  const logout = () => {
    clear();
    window.location.hash = "#/login";
  };

  const isFullBleed = isAuthed && path === "/";

  return (
    <div className="min-h-screen flex flex-col bg-canvas text-ink">
      <header className="sticky top-0 z-30 bg-canvas/80 backdrop-blur-md border-b border-ink/8">
        <div className="max-w-6xl mx-auto px-4 md:px-6 h-16 flex items-center justify-between gap-4">
          <a
            href="#/"
            className="flex items-center gap-2.5 font-medium text-ink hover:opacity-80 transition-opacity"
          >
            <span aria-hidden className="relative inline-block">
              <span className="inline-block w-7 h-7 rounded-full bg-leaf" />
              <span className="absolute inset-0.5 rounded-full bg-canvas grid place-items-center text-[12px] font-medium text-ink">
                u
              </span>
            </span>
            <span className="hidden sm:inline">{title}</span>
          </a>

          {isAuthed ? (
            <nav className="hidden md:flex items-center gap-1 text-sm">
              {NAV_ITEMS.map(({ href, label, match }) => {
                const active = match(path);
                return (
                  <a
                    key={href}
                    href={href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "px-3 py-1.5 rounded-btn transition-colors duration-180 ease-pirsch",
                      active
                        ? "bg-surface text-ink font-medium"
                        : "text-stone hover:text-ink hover:bg-surface/60",
                    )}
                  >
                    {label()}
                  </a>
                );
              })}
            </nav>
          ) : null}

          <div className="flex items-center gap-2">
            {isAuthed && (
              <button
                type="button"
                onClick={() => openCommandPalette()}
                aria-label="Buscar (Cmd+K)"
                data-tour="command-palette-trigger"
                className="hidden md:inline-flex items-center gap-2 h-9 pl-2.5 pr-2 rounded-btn bg-surface hover:bg-surface/70 text-stone hover:text-ink transition-colors duration-180 ease-pirsch"
              >
                <Search size={14} />
                <span className="text-xs">Buscar</span>
                <kbd className="text-[10px] bg-canvas px-1.5 py-0.5 rounded font-medium">⌘K</kbd>
              </button>
            )}
            {isAuthed && (
              <a
                href="#/universe"
                className="hidden lg:inline-flex items-center gap-2 h-9 px-3 rounded-btn bg-surface hover:bg-surface/70 transition-colors duration-180"
                title="Estado de tu perfil"
              >
                <CompletenessPill />
              </a>
            )}
            {isAuthed && (
              <span data-tour="reminders-bell">
                <NotificationCenter />
              </span>
            )}
            <ThemeToggle />
            <LanguageToggle
              value={i18n.resolvedLanguage || "es"}
              onChange={(v) => i18n.changeLanguage(v)}
            />
            {isAuthed ? (
              <>
                {email && (
                  <span className="hidden lg:inline text-xs text-stone max-w-[180px] truncate">
                    {email}
                  </span>
                )}
                <Button variant="ghost" size="sm" onClick={logout}>
                  Salir
                </Button>
              </>
            ) : (
              <div className="hidden sm:flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={() => (window.location.hash = "#/login")}>
                  Entrar
                </Button>
                <Button size="sm" onClick={() => (window.location.hash = "#/register")}>
                  Crear cuenta
                </Button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main
        className={cn(
          "flex-1 w-full",
          // When the chat is full-bleed (Home), don't add scroll padding bottom
          isAuthed && !isFullBleed && "pb-20 md:pb-0",
        )}
      >
        {children}
      </main>

      {!isFullBleed && (
        <footer className="border-t border-ink/5 bg-canvas py-6 mt-8 hidden md:block">
          <div className="max-w-6xl mx-auto px-4 md:px-6 text-xs text-stone flex flex-wrap gap-3 justify-between">
            <span>© {new Date().getFullYear()} Universo Profesional</span>
            <span className="flex gap-4">
              <a href="#/legal/terms" className="hover:text-ink transition-colors">
                Términos
              </a>
              <a href="#/legal/privacy" className="hover:text-ink transition-colors">
                Privacidad
              </a>
              <a href="#/legal/cookies" className="hover:text-ink transition-colors">
                Cookies
              </a>
            </span>
          </div>
        </footer>
      )}

      {isAuthed && <BottomNav />}
      <CookieConsentBanner />
    </div>
  );
}

function LanguageToggle({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const lang = value.startsWith("en") ? "en" : "es";
  return (
    <div
      role="group"
      aria-label="Idioma"
      className="inline-flex items-center gap-0.5 rounded-btn bg-surface p-0.5 text-[11px] font-medium"
    >
      {(["es", "en"] as const).map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(opt)}
          aria-pressed={lang === opt}
          className={cn(
            "px-2 py-1 rounded-[8px] transition-colors duration-180 uppercase tracking-wider",
            lang === opt ? "bg-canvas text-ink shadow-soft" : "text-stone hover:text-ink",
          )}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}
