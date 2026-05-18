import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { billing } from "@/shared/api";

export function BillingPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const plans = useQuery({ queryKey: ["billing", "plans"], queryFn: () => billing.plans() });
  const sub = useQuery({ queryKey: ["billing", "subscription"], queryFn: () => billing.subscription() });

  const upgrade = useMutation({
    mutationFn: (plan: "premium" | "pro") => billing.upgrade(plan),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["billing", "subscription"] }),
  });
  const cancel = useMutation({
    mutationFn: () => billing.cancel(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["billing", "subscription"] }),
  });

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      <header>
        <h1 className="text-2xl font-bold">{t("billing.title")}</h1>
        {sub.data && (
          <p className="text-sm text-gray-600 mt-2">
            Plan actual: <strong>{sub.data.plan}</strong> · estado: {sub.data.status}
            {sub.data.current_period_end && ` · hasta ${new Date(sub.data.current_period_end).toLocaleDateString()}`}
          </p>
        )}
      </header>

      <div className="grid md:grid-cols-3 gap-4">
        {plans.data?.plans.map((p) => (
          <div key={p.id} className="card flex flex-col">
            <h2 className="font-bold text-lg mb-1">{p.name}</h2>
            <p className="text-2xl font-bold mb-3">
              {p.price_eur_month === 0 ? "Gratis" : `${p.price_eur_month} €/mes`}
            </p>
            <ul className="text-sm space-y-1 flex-1 mb-3">
              <li>CVs/mes: {p.limits.monthly_cv === -1 ? "ilimitados" : p.limits.monthly_cv}</li>
              <li>Cartas/mes: {p.limits.monthly_cover_letters === -1 ? "ilimitadas" : p.limits.monthly_cover_letters}</li>
              <li>MCP: {p.limits.mcp_access ? `${p.limits.mcp_daily_calls}/día` : "no"}</li>
            </ul>
            {sub.data?.plan === p.id ? (
              <span className="badge-brand text-center">Tu plan</span>
            ) : p.id === "free" ? (
              <button onClick={() => cancel.mutate()} className="btn-secondary">Bajar a Free</button>
            ) : (
              <button onClick={() => upgrade.mutate(p.id as "premium" | "pro")} className="btn-primary">
                Mejorar a {p.name}
              </button>
            )}
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-500">
        En el MVP el pago está mockeado: el upgrade simula un webhook de Stripe Checkout
        completado para tu usuario, sin tarjeta real.
      </p>
    </div>
  );
}
