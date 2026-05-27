import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore, auth } from "@/shared/api";
import { useHashRoute } from "@/shared/useHashRoute";
import { useClickOutside } from "@/shared/useClickOutside";
import { useEscapeKey } from "@/shared/useEscapeKey";
import { useEnrichmentNotifications } from "@/shared/hooks/useEnrichmentNotifications";
import { queryKeys } from "@/shared/queryKeys";
import { Search, LogOut, BookOpen, ChevronDown } from "lucide-react";
import type { ReactNode } from "react";
import { Button, cn } from "@/ui";
import { BottomNav } from "./BottomNav";
import { openCommandPalette } from "./CommandPalette";
import { NotificationCenter } from "@/widgets/NotificationCenter";
import { CookieConsentBanner } from "@/widgets/CookieConsentBanner";
import { DiscoveryProgress, DiscoveryProgressPill } from "@/widgets/DiscoveryProgress";
import { ThemeToggle } from "./ThemeToggle";
import { tour } from "./tour/TourProvider";
import { firstRunTour } from "./tour/tours";

interface Props {
  title: string;
  isAuthed: boolean;
  children: ReactNode;
}

type NavItem = { href: string; label: string; match: (p: string) => boolean };

// Sections splay either side of the centred logo. "Documentos" now lives
// inside the universe; "Chat" is the home itself, so neither is a top item.
const NAV_LEFT: NavItem[] = [
  { href: "#/universe", label: "Universo", match: (p) => p.startsWith("/universe") },
  { href: "#/connections", label: "Conexiones", match: (p) => p.startsWith("/connections") },
];
const NAV_RIGHT: NavItem[] = [
  { href: "#/cv/new", label: "Generar CV", match: (p) => p.startsWith("/cv") },
  { href: "#/mcp", label: "MCP", match: (p) => p.startsWith("/mcp") },
];

export function Layout({ title, isAuthed, children }: Props) {
  const { i18n } = useTranslation();
  const path = useHashRoute();

  // Eagerly fetch the user profile so every page has it warm in the cache.
  useQuery({
    queryKey: queryKeys.me.all,
    queryFn: () => auth.me(),
    enabled: isAuthed,
    staleTime: 5 * 60_000,
    retry: 1,
  });

  // Watch for auto-enrichment results and notify the user.
  useEnrichmentNotifications();

  const isFullBleed = isAuthed && path === "/";

  return (
    <div className="min-h-screen flex flex-col bg-canvas text-ink">
      <header className="sticky top-0 z-30 bg-canvas/80 backdrop-blur-md hairline-b">
        <div className="mx-auto w-full max-w-7xl px-4 md:px-8 h-16 grid grid-cols-[1fr_auto_1fr] items-center gap-4">
          {/* Left zone: primary sections */}
          <nav className="hidden md:flex items-center gap-1 justify-self-start text-sm">
            {isAuthed &&
              NAV_LEFT.map((item) => <NavLink key={item.href} item={item} path={path} />)}
          </nav>

          {/* Center: logo (always centred) */}
          <a
            href="#/"
            className="justify-self-center flex items-center gap-2.5 font-medium text-ink hover:opacity-80 transition-opacity whitespace-nowrap"
          >
            <span aria-hidden className="relative inline-block">
              <span className="inline-block w-7 h-7 rounded-full bg-leaf" />
              <span className="absolute inset-0.5 rounded-full bg-canvas grid place-items-center text-[12px] font-medium text-ink">
                u
              </span>
            </span>
            <span className="hidden sm:inline font-display text-[19px] leading-none whitespace-nowrap">
              {title}
            </span>
          </a>

          {/* Right zone: sections + utility controls */}
          <div className="flex items-center gap-1 justify-self-end">
            {isAuthed && (
              <nav className="hidden lg:flex items-center gap-1 text-sm">
                {NAV_RIGHT.map((item) => (
                  <NavLink key={item.href} item={item} path={path} />
                ))}
                <span aria-hidden className="mx-1 h-5 w-px bg-hairline" />
              </nav>
            )}
            {isAuthed && (
              <button
                type="button"
                onClick={() => openCommandPalette()}
                aria-label="Buscar (Cmd+K)"
                data-tour="command-palette-trigger"
                className="hidden md:inline-flex items-center gap-2 h-9 pl-2.5 pr-2 rounded-btn text-stone hover:text-ink hover:bg-surface/70 transition-colors duration-180 ease-pirsch"
              >
                <Search size={14} />
                <span className="text-xs">Buscar</span>
                <kbd className="text-[10px] bg-surface px-1.5 py-0.5 rounded font-medium">⌘K</kbd>
              </button>
            )}
            {isAuthed && <DiscoveryProgressPill />}
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
              <AccountMenu />
            ) : (
              <div className="hidden sm:flex items-center gap-2 pl-1">
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
          isAuthed && !isFullBleed && "pb-20 md:pb-0",
        )}
      >
        {children}
      </main>

      {!isFullBleed && (
        <footer className="hairline-t bg-canvas py-6 mt-8 hidden md:block">
          <div className="max-w-7xl mx-auto px-4 md:px-8 text-xs text-stone flex flex-wrap gap-3 justify-between">
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
      {isAuthed && !path.startsWith("/universe") && (
        <div className="fixed right-4 top-24 z-20 w-[min(92vw,300px)] hidden lg:block">
          <DiscoveryProgress />
        </div>
      )}
      <CookieConsentBanner />
    </div>
  );
}

/** A single editorial nav link — underline on hover, solid rule when active. */
function NavLink({ item, path }: { item: NavItem; path: string }) {
  const active = item.match(path);
  return (
    <a
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "relative whitespace-nowrap shrink-0 px-3 py-1.5 transition-colors duration-180 ease-pirsch",
        "after:absolute after:left-3 after:right-3 after:-bottom-0.5 after:h-px after:origin-left after:transition-transform after:duration-180 after:ease-pirsch after:bg-ink",
        active
          ? "text-ink font-medium after:scale-x-100"
          : "text-stone hover:text-ink after:scale-x-0 hover:after:scale-x-100",
      )}
    >
      {item.label}
    </a>
  );
}

/** Account dropdown — consolidates email, "Ver tutorial" and Salir. */
function AccountMenu() {
  const { clear, email } = useAuthStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useClickOutside(ref, () => setOpen(false), open);
  useEscapeKey(() => setOpen(false), open);

  const logout = () => {
    clear();
    window.location.hash = "#/login";
  };

  const initial = (email?.[0] ?? "u").toUpperCase();

  return (
    <div className="relative ml-0.5" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Cuenta"
        className="flex items-center gap-1 rounded-full pl-0.5 pr-1.5 py-0.5 hover:bg-surface/70 transition-colors duration-180"
      >
        <span className="grid place-items-center w-8 h-8 rounded-full bg-ink text-canvas text-xs font-medium">
          {initial}
        </span>
        <ChevronDown
          size={14}
          className={cn("text-stone transition-transform duration-180", open && "rotate-180")}
        />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-2 w-60 rounded-card bg-canvas shadow-float border border-hairline p-1.5 z-50"
        >
          {email && (
            <div className="px-3 py-2 border-b border-hairline mb-1">
              <p className="eyebrow mb-1">Cuenta</p>
              <p className="text-sm text-ink truncate">{email}</p>
            </div>
          )}
          <a
            href="#/settings"
            role="menuitem"
            onClick={() => setOpen(false)}
            className="block px-3 py-2 rounded-btn text-sm text-stone hover:text-ink hover:bg-surface/70 transition-colors"
          >
            Ajustes
          </a>
          <a
            href="#/billing"
            role="menuitem"
            onClick={() => setOpen(false)}
            className="block px-3 py-2 rounded-btn text-sm text-stone hover:text-ink hover:bg-surface/70 transition-colors"
          >
            Plan y facturación
          </a>
          <a
            href="#/usage"
            role="menuitem"
            onClick={() => setOpen(false)}
            className="block px-3 py-2 rounded-btn text-sm text-stone hover:text-ink hover:bg-surface/70 transition-colors"
          >
            Uso de IA
          </a>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              tour.start(firstRunTour);
            }}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-btn text-sm text-stone hover:text-ink hover:bg-surface/70 transition-colors"
          >
            <BookOpen size={14} />
            Ver tutorial
          </button>
          <div className="my-1 border-t border-hairline" />
          <button
            type="button"
            role="menuitem"
            onClick={logout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-btn text-sm text-stone hover:text-ink hover:bg-surface/70 transition-colors"
          >
            <LogOut size={14} />
            Salir
          </button>
        </div>
      )}
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
      className="hidden sm:inline-flex items-center gap-0.5 rounded-btn bg-surface p-0.5 text-[11px] font-medium"
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
