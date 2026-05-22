import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { CheckCircle2, AlertTriangle, Info, X, Loader2 } from "lucide-react";
import { cn } from "./cn";

export type ToastVariant = "success" | "error" | "info" | "loading";

export interface Toast {
  id: string;
  variant: ToastVariant;
  title: string;
  description?: string;
  /** Auto-dismiss after N ms. 0 disables. Default 5000 (0 for loading). */
  duration?: number;
  /** Optional action button. */
  action?: { label: string; onClick: () => void };
}

interface ToasterContext {
  toast: (t: Omit<Toast, "id">) => string;
  update: (id: string, t: Partial<Omit<Toast, "id">>) => void;
  dismiss: (id: string) => void;
}

const Ctx = createContext<ToasterContext | null>(null);

let externalToaster: ToasterContext | null = null;

/**
 * Imperative API — usable outside React (api.ts, etc.).
 *
 *   toast.success("Guardado");
 *   const id = toast.loading("Subiendo…");
 *   toast.update(id, { variant: "success", title: "Subido" });
 */
export const toast = {
  show: (t: Omit<Toast, "id">) => externalToaster?.toast(t),
  success: (title: string, description?: string) =>
    externalToaster?.toast({ variant: "success", title, description }),
  error: (title: string, description?: string) =>
    externalToaster?.toast({ variant: "error", title, description, duration: 8000 }),
  info: (title: string, description?: string) =>
    externalToaster?.toast({ variant: "info", title, description }),
  loading: (title: string, description?: string) =>
    externalToaster?.toast({ variant: "loading", title, description, duration: 0 }),
  update: (id: string, t: Partial<Omit<Toast, "id">>) =>
    externalToaster?.update(id, t),
  dismiss: (id: string) => externalToaster?.dismiss(id),
};

export function useToaster(): ToasterContext {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useToaster must be used within ToasterProvider");
  return ctx;
}

export function ToasterProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toastFn = useCallback((t: Omit<Toast, "id">) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setToasts((arr) => [...arr, { ...t, id }]);
    return id;
  }, []);

  const update = useCallback((id: string, t: Partial<Omit<Toast, "id">>) => {
    setToasts((arr) => arr.map((x) => (x.id === id ? { ...x, ...t } : x)));
  }, []);

  const dismiss = useCallback((id: string) => {
    setToasts((arr) => arr.filter((x) => x.id !== id));
  }, []);

  const value = useMemo<ToasterContext>(
    () => ({ toast: toastFn, update, dismiss }),
    [toastFn, update, dismiss],
  );

  useEffect(() => {
    externalToaster = value;
    return () => {
      if (externalToaster === value) externalToaster = null;
    };
  }, [value]);

  return (
    <Ctx.Provider value={value}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismiss} />
    </Ctx.Provider>
  );
}

function ToastViewport({
  toasts,
  onDismiss,
}: {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}) {
  return (
    <div
      aria-live="polite"
      aria-atomic="false"
      className="fixed z-[70] pointer-events-none flex flex-col gap-2 top-4 right-4 max-w-[calc(100vw-2rem)] w-[360px]"
    >
      <AnimatePresence initial={false}>
        {toasts.map((t) => (
          <ToastCard key={t.id} toast={t} onDismiss={() => onDismiss(t.id)} />
        ))}
      </AnimatePresence>
    </div>
  );
}

function ToastCard({ toast: t, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  useEffect(() => {
    const duration = t.duration ?? (t.variant === "loading" ? 0 : 5000);
    if (duration <= 0) return;
    const handle = setTimeout(onDismiss, duration);
    return () => clearTimeout(handle);
  }, [t.duration, t.variant, onDismiss]);

  const meta = META[t.variant];
  const Icon = meta.Icon;
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: 24, scale: 0.96 }}
      transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
      role="status"
      className={cn(
        "pointer-events-auto rounded-card bg-canvas shadow-lift border border-ink/8 px-4 py-3 flex items-start gap-3",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "inline-flex items-center justify-center w-8 h-8 rounded-full shrink-0",
          meta.iconBg,
        )}
      >
        {t.variant === "loading" ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <Icon size={14} />
        )}
      </span>
      <div className="min-w-0 flex-1 space-y-0.5">
        <div className="text-sm font-medium text-ink leading-tight">{t.title}</div>
        {t.description && (
          <div className="text-xs text-stone leading-relaxed">{t.description}</div>
        )}
        {t.action && (
          <button
            type="button"
            onClick={() => {
              t.action!.onClick();
              onDismiss();
            }}
            className="mt-2 text-xs font-medium text-ink underline-offset-2 hover:underline"
          >
            {t.action.label}
          </button>
        )}
      </div>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Cerrar"
        className="shrink-0 w-7 h-7 -mr-1 inline-flex items-center justify-center rounded-full text-stone hover:text-ink hover:bg-black/[0.04] transition-colors duration-180"
      >
        <X size={14} />
      </button>
    </motion.div>
  );
}

const META: Record<ToastVariant, { Icon: typeof CheckCircle2; iconBg: string }> = {
  success: { Icon: CheckCircle2, iconBg: "bg-leaf-soft text-leaf-ink" },
  error: { Icon: AlertTriangle, iconBg: "bg-red-50 text-red-700" },
  info: { Icon: Info, iconBg: "bg-sunbeam-soft text-sunbeam-ink" },
  loading: { Icon: Loader2, iconBg: "bg-black/[0.04] text-stone" },
};
