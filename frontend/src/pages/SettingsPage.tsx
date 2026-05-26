import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Compass,
  Download,
  Mail,
  ShieldCheck,
  Sparkles,
  Trash2,
  User,
} from "lucide-react";
import { account, auth, useAuthStore } from "@/shared/api";
import { PhotoUpload } from "@/widgets/PhotoUpload";
import { tour } from "@/app/tour/TourProvider";
import { firstRunTour } from "@/app/tour/tours";
import { queryKeys } from "@/shared/queryKeys";
import {
  Badge,
  Button,
  Card,
  PageHeader,
  Reveal,
  Stagger,
  Surface,
  toast,
} from "@/ui";

export function SettingsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const me = useQuery({ queryKey: queryKeys.me.all, queryFn: () => auth.me() });
  const clear = useAuthStore((s) => s.clear);

  const setTier = useMutation({
    mutationFn: (tier: "free" | "pro") => account.setTier(tier),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.me.all }),
  });

  const exportData = async () => {
    const loadingId = toast.loading("Generando export…", "Empaquetando tu universo");
    try {
      const { accessToken } = useAuthStore.getState();
      const resp = await fetch("/api/v1/users/me/export", {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!resp.ok) {
        if (loadingId) toast.dismiss(loadingId);
        toast.error("No pudimos exportar tus datos", `HTTP ${resp.status}`);
        return;
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `cvs-saas-export.zip`;
      a.click();
      URL.revokeObjectURL(url);
      if (loadingId) toast.dismiss(loadingId);
      toast.success("Export descargado", "Cumple Art. 20 RGPD");
    } catch (e) {
      if (loadingId) toast.dismiss(loadingId);
      toast.error("Error al exportar", (e as Error).message);
    }
  };

  const deleteAccount = async () => {
    if (!confirm(t("settings.deleteConfirm"))) return;
    await auth.deleteMe();
    clear();
    window.location.hash = "#/";
  };

  const isPro = me.data?.tier === "pro";

  return (
    <Surface width="md" spacing="md">
      <PageHeader
        eyebrow="Cuenta"
        title={t("settings.title")}
        subtitle="Datos de tu cuenta, plan, exportación y borrado RGPD."
      />

      <Stagger className="flex flex-col gap-4 md:gap-6" delayStep={0.05}>
        <Card padding="lg">
          <SectionHeader icon={<User size={16} />} title="Foto de perfil" />
          <PhotoUpload />
        </Card>

        <Card padding="lg">
          <SectionHeader icon={<Mail size={16} />} title="Cuenta" />
          {me.data && (
            <dl className="text-sm grid grid-cols-3 gap-y-3 mt-1">
              <Row label="Email" value={me.data.email} />
              <Row label="Nombre" value={me.data.display_name ?? "—"} />
              <Row label="Locale" value={me.data.locale} />
              <Row
                label="Email verificado"
                value={
                  me.data.email_verified ? (
                    <Badge tone="leaf" size="sm" dot>
                      Verificado
                    </Badge>
                  ) : (
                    <Badge tone="amber" size="sm">
                      Pendiente
                    </Badge>
                  )
                }
              />
              <Row
                label="MFA"
                value={
                  me.data.mfa_enabled ? (
                    <Badge tone="leaf" size="sm">
                      Activo
                    </Badge>
                  ) : (
                    <Badge tone="stone" size="sm">
                      Desactivado
                    </Badge>
                  )
                }
              />
              <Row
                label="Desde"
                value={new Date(me.data.created_at).toLocaleString()}
              />
            </dl>
          )}
        </Card>

        <Card padding="lg" className="relative overflow-hidden">
          {isPro && (
            <div
              aria-hidden
              className="absolute -top-16 -right-16 w-56 h-56 rounded-full bg-sunbeam/30 blur-3xl"
            />
          )}
          <div className="relative">
            <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
              <SectionHeader
                icon={<Sparkles size={16} />}
                title="Plan"
                trailing={
                  isPro ? (
                    <Badge tone="sunbeam" dot>
                      PRO
                    </Badge>
                  ) : (
                    <Badge tone="stone">FREE</Badge>
                  )
                }
              />
            </div>
            <p className="text-sm text-stone mb-5 max-w-prose">
              {isPro
                ? "Tienes acceso a las integraciones avanzadas (Bright Data LinkedIn global, sin límite por usuario)."
                : "El plan FREE incluye DMA LinkedIn (UE), GitHub, ZIP, PDF. Pasa a PRO para sincronizar perfiles de LinkedIn globalmente vía Bright Data."}
            </p>
            {isPro ? (
              <Button
                variant="outline"
                onClick={() => setTier.mutate("free")}
                loading={setTier.isPending}
                title="En producción esto cancela la suscripción en Stripe."
              >
                {setTier.isPending ? "Cambiando" : "Volver a FREE (dev)"}
              </Button>
            ) : (
              <Button
                onClick={() => setTier.mutate("pro")}
                loading={setTier.isPending}
                title="En producción esto abriría Stripe."
              >
                {setTier.isPending ? "Activando" : "Pasar a PRO (dev)"}
              </Button>
            )}
          </div>
        </Card>

        <Card padding="lg">
          <SectionHeader icon={<Compass size={16} />} title="Tour guiado" />
          <p className="text-sm text-stone mb-5 max-w-prose">
            Repasa los cuatro puntos clave del producto en 30 segundos.
          </p>
          <Button
            variant="outline"
            leadingIcon={<Compass size={14} />}
            onClick={() => {
              window.location.hash = "#/";
              setTimeout(() => tour.start(firstRunTour), 250);
            }}
          >
            Volver a ver el tour
          </Button>
        </Card>

        <Card padding="lg">
          <SectionHeader icon={<ShieldCheck size={16} />} title="RGPD" />
          <p className="text-sm text-stone mb-5 max-w-prose">
            Descarga todos tus datos en un archivo ZIP. Cumple Art. 20 (portabilidad).
          </p>
          <Button onClick={exportData} leadingIcon={<Download size={14} />}>
            {t("settings.exportRgpd")}
          </Button>
        </Card>

        <Reveal delay={0.15}>
          <Card padding="lg" className="border border-red-200/70 bg-red-50/40">
            <SectionHeader
              icon={<AlertTriangle size={16} className="text-red-700" />}
              title="Zona peligrosa"
              titleClass="text-red-700"
            />
            <p className="text-sm text-red-700/80 mb-5 max-w-prose">
              La cuenta se marca como borrada inmediatamente. Tras 30 días se elimina
              físicamente (Art. 17 RGPD: derecho al olvido).
            </p>
            <Button
              variant="danger"
              onClick={deleteAccount}
              leadingIcon={<Trash2 size={14} />}
            >
              {t("settings.deleteAccount")}
            </Button>
          </Card>
        </Reveal>
      </Stagger>
    </Surface>
  );
}

function SectionHeader({
  icon,
  title,
  trailing,
  titleClass,
}: {
  icon: React.ReactNode;
  title: string;
  trailing?: React.ReactNode;
  titleClass?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3 mb-4">
      <div className="flex items-center gap-3">
        <span
          aria-hidden
          className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-canvas text-ink"
        >
          {icon}
        </span>
        <h2 className={`text-heading-sm font-medium tracking-tight ${titleClass ?? "text-ink"}`}>
          {title}
        </h2>
      </div>
      {trailing}
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt className="text-stone text-xs uppercase tracking-wider self-center">{label}</dt>
      <dd className="col-span-2 text-ink break-words">{value}</dd>
    </>
  );
}
