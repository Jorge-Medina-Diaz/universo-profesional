import { useEffect, useRef, useState, type MouseEvent } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Menu, X, ArrowRight, Sun, Moon } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useTheme } from "@/shared/useTheme";

/** i18n keys in the landing namespace; resolved inside SiteNav. */
const LINKS = [
  { key: "nav.memory", href: "#memoria" },
  { key: "nav.twin", href: "#twin" },
  { key: "nav.payoff", href: "#payoff" },
  { key: "nav.pricing", href: "#precios" },
];

function LanguageSwitch({ className = "" }: { className?: string }) {
  const { i18n } = useTranslation("landing");
  const isEn = i18n.language.startsWith("en");
  const set = (lang: "es" | "en") => {
    void i18n.changeLanguage(lang);
    document.documentElement.lang = lang;
  };
  return (
    <div
      className={`inline-flex items-center rounded-full border border-[var(--cos-hairline)] p-0.5 text-[11px] font-mono ${className}`}
      role="group"
      aria-label="Idioma"
    >
      {(["es", "en"] as const).map((lang) => (
        <button
          key={lang}
          type="button"
          aria-pressed={lang === "en" ? isEn : !isEn}
          onClick={() => set(lang)}
          className={`px-2.5 py-1 rounded-full uppercase transition-colors ${
            (lang === "en") === isEn
              ? "bg-[var(--cos-fill-strong)] text-[var(--cos-ink)]"
              : "text-[var(--cos-stone)] hover:text-[var(--cos-ink)]"
          }`}
        >
          {lang}
        </button>
      ))}
    </div>
  );
}

function go(hash: string) {
  window.location.hash = hash;
}

/**
 * Smooth-scroll to an in-page section instead of letting the hash router treat
 * the anchor as a route. We preventDefault (so no `hashchange` fires) and use
 * replaceState to keep the anchor in the URL without a route churn.
 */
function scrollToSection(e: MouseEvent<HTMLAnchorElement>, href: string) {
  const el = document.getElementById(href.replace(/^#/, ""));
  if (!el) return; // let the browser handle unknown anchors
  e.preventDefault();
  el.scrollIntoView({ behavior: "smooth", block: "start" });
  history.replaceState(null, "", href);
}

function ThemeToggleButton({ className = "" }: { className?: string }) {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isDark ? "Activar tema claro" : "Activar tema oscuro"}
      aria-pressed={isDark}
      className={`grid h-10 w-10 place-items-center rounded-full border border-[var(--cos-hairline)] text-[var(--cos-stone)] transition-colors hover:text-[var(--cos-ink)] hover:bg-[var(--cos-fill-strong)] ${className}`}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={isDark ? "moon" : "sun"}
          initial={{ opacity: 0, rotate: -90, scale: 0.6 }}
          animate={{ opacity: 1, rotate: 0, scale: 1 }}
          exit={{ opacity: 0, rotate: 90, scale: 0.6 }}
          transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
          aria-hidden
        >
          {isDark ? <Moon size={16} /> : <Sun size={16} />}
        </motion.span>
      </AnimatePresence>
    </button>
  );
}

export function SiteNav() {
  const { t } = useTranslation("landing");
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const sheetRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  // Focus management for the mobile sheet: trap Tab within it while open and
  // close on Escape. Focus the first interactive element on open.
  useEffect(() => {
    if (!open) return;
    const sheet = sheetRef.current;
    if (!sheet) return;

    const focusable = () =>
      Array.from(
        sheet.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((el) => el.offsetParent !== null);

    focusable()[0]?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setOpen(false);
        return;
      }
      if (e.key !== "Tab") return;
      const items = focusable();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement;
      if (e.shiftKey) {
        if (active === first || !sheet.contains(active)) {
          e.preventDefault();
          last.focus();
        }
      } else if (active === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <>
      <motion.header
        initial={{ y: -24, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.2, 0.8, 0.2, 1] }}
        className="fixed inset-x-0 top-0 z-50"
      >
        {/* Skip-to-content — first focusable element, hidden until focused */}
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[70] focus:rounded-full focus:border focus:border-[var(--cos-hairline-strong)] focus:bg-[var(--cos-bg-2)] focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-[var(--cos-ink)]"
        >
          Saltar al contenido
        </a>
        <div
          className={`mx-auto flex max-w-7xl items-center justify-between px-5 transition-all duration-300 md:px-8 ${
            scrolled ? "py-3" : "py-5"
          }`}
        >
          {/* Brand */}
          <a
            href="#top"
            onClick={(e) => {
              e.preventDefault();
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
            className="group flex items-center gap-2.5"
          >
            <span className="relative grid h-7 w-7 place-items-center">
              <span className="absolute h-2.5 w-2.5 rounded-full bg-[#ffda6e] shadow-[0_0_14px_2px_rgba(255,218,110,0.7)]" />
              <span className="absolute h-7 w-7 rounded-full border border-[var(--cos-hairline-strong)]" />
              <span className="absolute h-1 w-1 -translate-x-3 -translate-y-1.5 rounded-full bg-[#6ece9d]" />
              <span className="absolute h-1 w-1 translate-x-2.5 translate-y-2 rounded-full bg-[#00d4aa]" />
            </span>
            <span className="cos-display text-[17px] tracking-tight text-[var(--cos-ink)]">
              Universo
            </span>
          </a>

          {/* Center links — floating glass pill */}
          <nav
            className={`pointer-events-auto absolute left-1/2 hidden -translate-x-1/2 items-center gap-1 rounded-full border px-2 py-1.5 backdrop-blur-md transition-all duration-300 lg:flex ${
              scrolled
                ? "border-[var(--cos-hairline)] bg-[var(--cos-fill-strong)]"
                : "border-transparent bg-transparent"
            }`}
          >
            {LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                onClick={(e) => scrollToSection(e, l.href)}
                className="rounded-full px-3.5 py-1.5 text-sm text-[var(--cos-stone)] transition-colors hover:bg-[var(--cos-fill-strong)] hover:text-[var(--cos-ink)]"
              >
                {t(l.key)}
              </a>
            ))}
          </nav>

          {/* Right actions */}
          <div className="flex items-center gap-2">
            <LanguageSwitch className="hidden md:inline-flex" />
            <button
              onClick={() => go("#/login")}
              className="hidden rounded-full px-4 py-2 text-sm font-medium text-[var(--cos-stone)] transition-colors hover:text-[var(--cos-ink)] sm:block"
            >
              {t("nav.login")}
            </button>
            <button
              onClick={() => go("#/register")}
              className="group hidden items-center gap-1.5 rounded-full bg-[var(--cos-ink)] px-4 py-2 text-sm font-semibold text-[var(--cos-on-ink)] transition-transform hover:-translate-y-0.5 sm:inline-flex"
            >
              {t("nav.cta")}
              <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
            </button>
            <button
              aria-label="Abrir menú"
              onClick={() => setOpen(true)}
              className="grid h-10 w-10 place-items-center rounded-full border border-[var(--cos-hairline)] text-[var(--cos-ink)] lg:hidden"
            >
              <Menu size={18} />
            </button>
          </div>
        </div>
        {/* hairline that appears once scrolled */}
        <div
          className={`mx-auto h-px max-w-7xl bg-[var(--cos-hairline)] transition-opacity duration-300 ${
            scrolled ? "opacity-100" : "opacity-0"
          }`}
        />
      </motion.header>

      {/* Mobile sheet */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="fixed inset-0 z-[60] lg:hidden"
          >
            <div
              className="absolute inset-0 bg-[var(--cos-scrim)] backdrop-blur-sm"
              onClick={() => setOpen(false)}
            />
            <motion.nav
              ref={sheetRef}
              role="dialog"
              aria-modal="true"
              aria-label="Menú de navegación"
              initial={{ y: -16, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: -16, opacity: 0 }}
              transition={{ duration: 0.3, ease: [0.2, 0.8, 0.2, 1] }}
              className="absolute inset-x-3 top-3 overflow-hidden rounded-3xl border border-[var(--cos-hairline-strong)] bg-[var(--cos-bg-2)] p-3"
            >
              <div className="flex items-center justify-between px-2 py-1.5">
                <span className="cos-display text-base text-[var(--cos-ink)]">Universo</span>
                <div className="flex items-center gap-2">
                  <ThemeToggleButton />
                  <button
                    aria-label="Cerrar menú"
                    onClick={() => setOpen(false)}
                    className="grid h-9 w-9 place-items-center rounded-full border border-[var(--cos-hairline)] text-[var(--cos-ink)]"
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>
              <div className="mt-2 flex flex-col">
                {LINKS.map((l) => (
                  <a
                    key={l.href}
                    href={l.href}
                    onClick={(e) => {
                      setOpen(false);
                      scrollToSection(e, l.href);
                    }}
                    className="rounded-2xl px-3 py-3 text-[15px] text-[var(--cos-ink)] transition-colors hover:bg-[var(--cos-fill-strong)]"
                  >
                    {t(l.key)}
                  </a>
                ))}
              </div>
              <div className="mt-2 grid grid-cols-1 gap-2 p-1">
                <button
                  onClick={() => {
                    setOpen(false);
                    go("#/register");
                  }}
                  className="cos-btn-primary w-full"
                >
                  {t("nav.cta")}
                </button>
                <button
                  onClick={() => {
                    setOpen(false);
                    go("#/login");
                  }}
                  className="cos-btn-ghost w-full"
                >
                  {t("nav.login")}
                </button>
                <div className="flex justify-center pt-1">
                  <LanguageSwitch />
                </div>
              </div>
            </motion.nav>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
