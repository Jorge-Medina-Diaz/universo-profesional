import { useEffect, useMemo, useState } from "react";
import { Check, CreditCard, Loader2 } from "lucide-react";
import { api } from "@/shared/api";
import { Button, Card } from "@/ui";

const PLAN_NAMES: Record<string, string> = {
  premium: "Premium",
  pro: "Pro",
};

const PLAN_PRICES: Record<string, string> = {
  premium: "9,99 €/mes",
  pro: "19,99 €/mes",
};

export function CheckoutMockPage() {
  const query = useMemo(() => {
    // The app uses a hash router, so params live in the hash fragment
    // (e.g. "#/billing/checkout-mock?plan=pro"), not window.location.search.
    const q = (window.location.hash || "").split("?")[1] ?? "";
    const params = new URLSearchParams(q);
    return {
      plan: params.get("plan") ?? "premium",
      userId: params.get("user_id") ?? "",
      returnUrl: params.get("return_url") ?? "#/billing",
    };
  }, []);

  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.title = `Pago simulado — ${PLAN_NAMES[query.plan] ?? query.plan}`;
  }, [query.plan]);

  const handleConfirm = async () => {
    setStatus("loading");
    setError(null);
    try {
      await api("/api/v1/billing/webhook/test", {
        method: "POST",
        body: JSON.stringify({
          event: "checkout.completed",
          user_id: query.userId,
          plan: query.plan,
        }),
      });
      setStatus("success");
      setTimeout(() => {
        window.location.href = query.returnUrl;
      }, 1500);
    } catch (e) {
      setStatus("error");
      setError(e instanceof Error ? e.message : "Error desconocido");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-canvas">
      <Card className="w-full max-w-md">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-sunbeam/20 text-ink mb-4">
            <CreditCard size={24} />
          </div>
          <h1 className="text-xl font-semibold text-ink">Simulación de pago</h1>
          <p className="text-stone text-sm mt-1">
            Modo desarrollo — no se cargará ninguna tarjeta real.
          </p>
        </div>

        <div className="bg-surface border border-hairline rounded-lg p-4 mb-6">
          <div className="flex justify-between items-center">
            <span className="text-ink font-medium">Plan {PLAN_NAMES[query.plan] ?? query.plan}</span>
            <span className="text-ink font-semibold">{PLAN_PRICES[query.plan] ?? ""}</span>
          </div>
        </div>

        {status === "success" ? (
          <div className="text-center py-4">
            <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-leaf/20 text-ink mb-3">
              <Check size={20} />
            </div>
            <p className="text-ink font-medium">¡Pago simulado correcto!</p>
            <p className="text-stone text-sm mt-1">Redirigiendo…</p>
          </div>
        ) : (
          <>
            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                {error}
              </p>
            )}
            <Button
              onClick={handleConfirm}
              loading={status === "loading"}
              disabled={status === "loading"}
              className="w-full"
            >
              {status === "loading" ? (
                <>
                  <Loader2 size={16} className="animate-spin mr-2" />
                  Procesando…
                </>
              ) : (
                "Confirmar pago simulado"
              )}
            </Button>
            <Button
              variant="ghost"
              className="w-full mt-2"
              onClick={() => {
                window.location.href = query.returnUrl;
              }}
            >
              Cancelar y volver
            </Button>
          </>
        )}
      </Card>
    </div>
  );
}
