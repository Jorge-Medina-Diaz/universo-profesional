import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Check, ExternalLink, Sparkles, Infinity as InfinityIcon } from "lucide-react";
import { billing } from "@/shared/api";
import {
  Badge,
  Button,
  Card,
  PageHeader,
  Reveal,
  Stagger,
  Surface,
  cn,
  toast,
} from "@/ui";
import { queryKeys } from "@/shared/queryKeys";

interface Plan {
  id: string;
  name: string;
  price_eur_month: number;
  limits: {
    monthly_cv: number;
    monthly_cover_letters: number;
    mcp_access: boolean;
    mcp_daily_calls: number;
  };
}

export function BillingPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const plans = useQuery({ queryKey: queryKeys.billing.plans, queryFn: () => billing.plans() });
  const sub = useQuery({
    queryKey: queryKeys.billing.subscription,
    queryFn: () => billing.subscription(),
  });

  const upgrade = useMutation({
    mutationFn: (plan: "premium" | "pro") => billing.checkout(plan),
    onSuccess: (data) => {
      // Stripe returns a hosted checkout URL; in mock mode it's a local
      // dev path. Either way, we navigate the browser.
      if (data?.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        toast.error("No pudimos iniciar el checkout");
      }
    },
    onError: (e: unknown) => {
      toast.error("Error en checkout", (e as Error).message);
    },
  });
  const portal = useMutation({
    mutationFn: () => billing.portal(`${window.location.origin}/#/billing`),
    onSuccess: (data) => {
      if (data?.portal_url) window.location.href = data.portal_url;
    },
    onError: (e: unknown) =>
      toast.error("No pudimos abrir el portal", (e as Error).message),
  });
  const cancel = useMutation({
    mutationFn: () => billing.cancel(),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.billing.subscription }),
    onError: (e: unknown) =>
      toast.error("No se pudo cancelar la suscripción", (e as Error).message),
  });

  return (
    <Surface width="lg" spacing="md">
      <PageHeader
        eyebrow="Suscripción"
        title={t("billing.title")}
        subtitle={
          sub.data && (
            <>
              Plan actual: <strong>{sub.data.plan}</strong> · estado: {sub.data.status}
              {sub.data.current_period_end &&
                ` · hasta ${new Date(sub.data.current_period_end).toLocaleDateString()}`}
            </>
          )
        }
      />

      {sub.data?.status === "trialing" && sub.data?.trial_ends_at && (
        <Reveal delay={0.1}>
          <Card
            tone="glass"
            padding="md"
            className="bg-sunbeam/10 border-sunbeam/30 flex items-center justify-between gap-4 flex-wrap"
          >
            <div>
              <h3 className="text-sm font-medium text-ink">
                Estás en tu prueba gratuita de Premium
              </h3>
              <p className="text-xs text-stone mt-0.5">
                Finaliza el {new Date(sub.data.trial_ends_at).toLocaleDateString()}.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => portal.mutate()}
              loading={portal.isPending}
            >
              Gestionar suscripción
            </Button>
          </Card>
        </Reveal>
      )}

      <Stagger className="grid md:grid-cols-3 gap-4 md:gap-6" delayStep={0.07}>
        {plans.data?.plans.map((p: Plan) => {
          const isCurrent = sub.data?.plan === p.id;
          const isPro = p.id === "pro";
          return (
            <PlanCard
              key={p.id}
              plan={p}
              isCurrent={isCurrent}
              highlighted={isPro}
              onUpgrade={
                p.id === "free"
                  ? () => cancel.mutate()
                  : () => upgrade.mutate(p.id as "premium" | "pro")
              }
              upgradeLoading={p.id === "free" ? cancel.isPending : upgrade.isPending}
              upgradeLabel={
                p.id === "free" ? "Bajar a Free" : `Mejorar a ${p.name}`
              }
            />
          );
        })}
      </Stagger>

      {sub.data && sub.data.plan !== "free" && (
        <Reveal delay={0.2}>
          <Card padding="md" className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h3 className="text-sm font-medium text-ink">Gestionar suscripción</h3>
              <p className="text-xs text-stone mt-0.5">
                Cambia método de pago, descarga facturas o cancela desde el portal de Stripe.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => portal.mutate()}
              loading={portal.isPending}
              leadingIcon={<ExternalLink size={12} />}
            >
              Abrir portal
            </Button>
          </Card>
        </Reveal>
      )}

      <Reveal delay={0.25}>
        <p className="text-xs text-stone text-center">
          Pagos seguros vía Stripe. Puedes cancelar cuando quieras desde el portal.
        </p>
      </Reveal>
    </Surface>
  );
}

function PlanCard({
  plan,
  isCurrent,
  highlighted,
  onUpgrade,
  upgradeLoading,
  upgradeLabel,
}: {
  plan: Plan;
  isCurrent: boolean;
  highlighted: boolean;
  onUpgrade: () => void;
  upgradeLoading: boolean;
  upgradeLabel: string;
}) {
  return (
    <Card
      tone={highlighted ? "glass" : "surface"}
      padding="lg"
      className={cn(
        "flex flex-col gap-5 relative overflow-hidden",
        highlighted && "ring-1 ring-sunbeam/40",
      )}
    >
      {highlighted && (
        <div
          aria-hidden
          className="absolute -top-16 -right-16 w-40 h-40 rounded-full bg-sunbeam/30 blur-3xl"
        />
      )}
      <div className="relative space-y-3">
        <div className="flex items-center gap-2">
          <h2 className="text-heading-sm font-medium tracking-tight">{plan.name}</h2>
          {highlighted && (
            <Badge tone="sunbeam" size="sm" icon={<Sparkles size={10} />}>
              Recomendado
            </Badge>
          )}
        </div>
        <div className="flex items-end gap-1">
          {plan.price_eur_month === 0 ? (
            <span className="text-[40px] md:text-[44px] font-medium leading-none tracking-tight">
              Gratis
            </span>
          ) : (
            <>
              <span className="text-[44px] font-medium leading-none tracking-tight">
                {plan.price_eur_month}
              </span>
              <span className="text-stone text-sm mb-1">€/mes</span>
            </>
          )}
        </div>
      </div>
      <ul className="relative text-sm space-y-2.5 flex-1">
        <Feature
          text={
            plan.limits.monthly_cv === -1
              ? "CVs ilimitados"
              : `${plan.limits.monthly_cv} CVs / mes`
          }
          infinite={plan.limits.monthly_cv === -1}
        />
        <Feature
          text={
            plan.limits.monthly_cover_letters === -1
              ? "Cartas ilimitadas"
              : `${plan.limits.monthly_cover_letters} cartas / mes`
          }
          infinite={plan.limits.monthly_cover_letters === -1}
        />
        <Feature
          text={
            plan.limits.mcp_access
              ? `MCP: ${plan.limits.mcp_daily_calls} llamadas/día`
              : "MCP no disponible"
          }
          disabled={!plan.limits.mcp_access}
        />
      </ul>
      <div className="relative">
        {isCurrent ? (
          <Badge tone="leaf" dot className="w-full justify-center py-2">
            Tu plan actual
          </Badge>
        ) : (
          <Button
            fullWidth
            variant={highlighted ? "cta" : "outline"}
            onClick={onUpgrade}
            loading={upgradeLoading}
          >
            {upgradeLabel}
          </Button>
        )}
      </div>
    </Card>
  );
}

function Feature({
  text,
  infinite,
  disabled,
}: {
  text: string;
  infinite?: boolean;
  disabled?: boolean;
}) {
  return (
    <li
      className={cn(
        "flex items-center gap-2.5",
        disabled ? "text-stone line-through" : "text-ink",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "inline-flex items-center justify-center w-5 h-5 rounded-full shrink-0",
          disabled ? "bg-black/[0.04] text-stone" : "bg-leaf-soft text-leaf-ink",
        )}
      >
        {infinite ? <InfinityIcon size={12} /> : <Check size={12} strokeWidth={2.5} />}
      </span>
      <span>{text}</span>
    </li>
  );
}
