/**
 * GDPR cookie/consent banner.
 *
 * Three buckets:
 *   * Necessary — auth, CSRF. Always on (no toggle).
 *   * Analytics — Sentry error reporting + (future) usage analytics.
 *   * Marketing — currently unused but reserved for future ad-pixel rerolls.
 *
 * Stored in localStorage so the choice survives between sessions. The
 * banner unmounts itself once a decision has been recorded. The Sentry
 * setup in `shared/sentry.ts` reads the same localStorage key to gate
 * initialization.
 */
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Cookie, Settings2 } from "lucide-react";
import { Button, cn } from "@/ui";

const STORAGE_KEY = "cvs-saas-cookie-consent";

interface Consent {
  necessary: true;
  analytics: boolean;
  marketing: boolean;
  decided_at: string;
}

function loadConsent(): Consent | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as Consent;
  } catch {
    return null;
  }
}

function saveConsent(consent: Omit<Consent, "necessary" | "decided_at">): void {
  const full: Consent = {
    necessary: true,
    decided_at: new Date().toISOString(),
    ...consent,
  };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(full));
  } catch {
    /* private mode — silently ignore */
  }
}

async function rebootObservability(): Promise<void> {
  // Lazy import so the bundle stays small when consent is denied.
  try {
    const { initSentry } = await import("@/shared/sentry");
    await initSentry();
  } catch {
    /* sentry stub missing — ok */
  }
}

export function CookieConsentBanner() {
  const [open, setOpen] = useState(() => loadConsent() === null);
  const [showPrefs, setShowPrefs] = useState(false);
  const [analytics, setAnalytics] = useState(true);
  const [marketing, setMarketing] = useState(false);

  // Re-check on mount in case another tab already decided.
  useEffect(() => {
    if (loadConsent()) setOpen(false);
  }, []);

  if (!open) return null;

  const decide = async (a: boolean, m: boolean) => {
    saveConsent({ analytics: a, marketing: m });
    setOpen(false);
    if (a) await rebootObservability();
  };

  return (
    <AnimatePresence>
      <motion.div
        role="dialog"
        aria-modal="false"
        aria-labelledby="cookie-banner-title"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 8 }}
        transition={{ duration: 0.28, ease: [0.2, 0.8, 0.2, 1] }}
        className="fixed bottom-4 left-4 right-4 md:left-auto md:right-6 md:bottom-6 z-50 max-w-md rounded-card bg-canvas border border-ink/15 shadow-lift p-5"
      >
        <header className="flex items-start gap-3 mb-3">
          <span
            aria-hidden
            className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-sunbeam-soft text-sunbeam-ink shrink-0"
          >
            <Cookie size={16} />
          </span>
          <div className="min-w-0">
            <h2 id="cookie-banner-title" className="text-sm font-medium text-ink leading-tight">
              Cookies y privacidad
            </h2>
            <p className="text-xs text-stone mt-1 leading-relaxed">
              Usamos cookies necesarias para que la app funcione. Las de
              diagnóstico nos ayudan a corregir errores; las de marketing
              están desactivadas por defecto.
            </p>
          </div>
        </header>

        <AnimatePresence initial={false}>
          {showPrefs && (
            <motion.div
              key="prefs"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
              className="overflow-hidden"
            >
              <ul className="space-y-2 text-xs my-3 border-t border-ink/5 pt-3">
                <Row
                  label="Necesarias"
                  description="Sesión y CSRF. No se pueden desactivar."
                  checked
                  disabled
                />
                <Row
                  label="Diagnóstico"
                  description="Sentry — informes anónimos de errores."
                  checked={analytics}
                  onChange={setAnalytics}
                />
                <Row
                  label="Marketing"
                  description="No usadas hoy. Reservado para futuras campañas."
                  checked={marketing}
                  onChange={setMarketing}
                />
              </ul>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex gap-2 flex-wrap mt-3">
          <Button
            size="sm"
            onClick={() => void decide(true, true)}
            className="flex-1"
          >
            Aceptar todo
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => void decide(false, false)}
          >
            Solo necesarias
          </Button>
          {!showPrefs ? (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowPrefs(true)}
              leadingIcon={<Settings2 size={12} />}
            >
              Personalizar
            </Button>
          ) : (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => void decide(analytics, marketing)}
            >
              Guardar
            </Button>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

function Row({
  label,
  description,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onChange?: (next: boolean) => void;
}) {
  return (
    <li className="flex items-start gap-3">
      <label
        className={cn(
          "relative inline-flex items-center cursor-pointer mt-0.5 shrink-0",
          disabled && "opacity-60 cursor-not-allowed",
        )}
      >
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange?.(e.target.checked)}
          className="sr-only peer"
        />
        <span className="block w-9 h-5 rounded-full bg-black/[0.08] peer-checked:bg-leaf transition-colors duration-180" />
        <span
          aria-hidden
          className="absolute left-0.5 top-0.5 w-4 h-4 rounded-full bg-canvas shadow-soft transition-transform duration-180 peer-checked:translate-x-4"
        />
      </label>
      <div className="min-w-0">
        <div className="text-ink font-medium">{label}</div>
        <div className="text-stone leading-relaxed">{description}</div>
      </div>
    </li>
  );
}
