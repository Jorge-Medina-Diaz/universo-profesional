/**
 * Global upgrade prompt.
 *
 * Any API call that hits a quota/tier wall returns HTTP 402; the api() wrapper
 * (shared/api.ts) dispatches a `cvs:upgrade-required` window event with the
 * problem-detail body. This single top-level listener turns every such wall
 * into one conversion moment — no per-call wiring needed.
 */
import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { Button, Dialog } from "@/ui";

interface QuotaDetail {
  title?: string;
  detail?: string;
  code?: string;
  required_tier?: string;
  message?: string;
}

export function UpgradeModal() {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<QuotaDetail | null>(null);

  useEffect(() => {
    const onUpgrade = (e: Event) => {
      const payload = (e as CustomEvent).detail as QuotaDetail | undefined;
      setDetail(payload ?? null);
      setOpen(true);
    };
    window.addEventListener("cvs:upgrade-required", onUpgrade);
    return () => window.removeEventListener("cvs:upgrade-required", onUpgrade);
  }, []);

  // Prefer the server's human message, falling back to a sensible default.
  const message =
    detail?.message ||
    detail?.detail ||
    detail?.title ||
    "Has alcanzado el límite de tu plan gratuito.";

  return (
    <Dialog open={open} onClose={() => setOpen(false)} title="Mejora tu plan">
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <span
            aria-hidden
            className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-sunbeam-soft text-sunbeam-ink shrink-0"
          >
            <Sparkles size={18} />
          </span>
          <p className="text-sm text-stone leading-relaxed">{message}</p>
        </div>
        <p className="text-sm text-stone">
          Con un plan de pago obtienes CVs y cartas ilimitados, acceso MCP y las
          integraciones avanzadas.
        </p>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Ahora no
          </Button>
          <Button
            variant="cta"
            onClick={() => {
              setOpen(false);
              window.location.hash = "#/billing";
            }}
          >
            Ver planes
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
