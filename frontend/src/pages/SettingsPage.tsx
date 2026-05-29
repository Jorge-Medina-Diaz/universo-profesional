import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bell,
  Compass,
  Download,
  KeyRound,
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
  Input,
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
  const [deleting, setDeleting] = useState(false);

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
    setDeleting(true);
    try {
      await auth.deleteMe();
      clear();
      window.location.hash = "#/";
    } catch (e) {
      setDeleting(false);
      toast.error("No pudimos borrar tu cuenta", (e as Error).message);
    }
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
                label="MFA (2FA)"
                value={
                  me.data.mfa_enabled ? (
                    <Badge tone="leaf" size="sm" dot>
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
                variant="cta"
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
          <SectionHeader icon={<ShieldCheck size={16} />} title="Verificación en dos pasos (2FA)" />
          <MfaCard
            enabled={me.data?.mfa_enabled ?? false}
            onChanged={() => qc.invalidateQueries({ queryKey: queryKeys.me.all })}
          />
        </Card>

        <Card padding="lg">
          <SectionHeader
            icon={<KeyRound size={16} />}
            title="Clave de IA propia (BYOK)"
            trailing={!isPro ? <Badge tone="sunbeam">PRO</Badge> : undefined}
          />
          <ByokCard isPro={isPro} />
        </Card>

        <Card padding="lg">
          <SectionHeader icon={<Bell size={16} />} title="Notificaciones" />
          <p className="text-sm text-stone mb-5 max-w-prose">
            Gestiona tus recordatorios (certificaciones por caducar, cursos en
            pausa) y el resumen diario por email.
          </p>
          <Button
            variant="outline"
            leadingIcon={<Bell size={14} />}
            onClick={() => (window.location.hash = "#/reminders")}
          >
            Gestionar recordatorios
          </Button>
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
              loading={deleting}
              disabled={deleting}
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

function MfaCard({ enabled, onChanged }: { enabled: boolean; onChanged: () => void }) {
  const [mode, setMode] = useState<"idle" | "enrolling" | "disabling">("idle");
  const [secret, setSecret] = useState<string | null>(null);
  const [uri, setUri] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);

  const reset = () => {
    setMode("idle");
    setSecret(null);
    setUri(null);
    setCode("");
  };

  const startEnroll = async () => {
    setBusy(true);
    try {
      const r = await auth.mfa.setup();
      setSecret(r.secret);
      setUri(r.otpauth_uri);
      setMode("enrolling");
    } catch (e) {
      toast.error("No pudimos iniciar el 2FA", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    setBusy(true);
    try {
      await auth.mfa.confirm(code);
      toast.success("2FA activado", "Te pediremos un código al iniciar sesión.");
      reset();
      onChanged();
    } catch (e) {
      toast.error("Código incorrecto", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const disable = async () => {
    setBusy(true);
    try {
      await auth.mfa.disable(code);
      toast.success("2FA desactivado");
      reset();
      onChanged();
    } catch (e) {
      toast.error("No pudimos desactivar el 2FA", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const CodeInput = (
    <Input
      inputMode="numeric"
      pattern="[0-9]*"
      maxLength={6}
      autoComplete="one-time-code"
      value={code}
      onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
      placeholder="123456"
      className="max-w-[160px] tracking-[0.3em] text-center"
    />
  );

  // Enabled → offer disable (code-gated).
  if (enabled) {
    if (mode === "disabling") {
      return (
        <div className="space-y-3">
          <p className="text-sm text-stone max-w-prose">
            Introduce un código de tu app de autenticación para desactivar el 2FA.
          </p>
          {CodeInput}
          <div className="flex gap-2">
            <Button variant="danger" onClick={disable} loading={busy} disabled={code.length < 6}>
              Desactivar 2FA
            </Button>
            <Button variant="ghost" onClick={reset} disabled={busy}>
              Cancelar
            </Button>
          </div>
        </div>
      );
    }
    return (
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <p className="text-sm text-stone max-w-prose">
          El 2FA está <span className="text-ink font-medium">activo</span>. Pedimos un
          código de tu app al iniciar sesión.
        </p>
        <Button variant="outline" onClick={() => setMode("disabling")}>
          Desactivar
        </Button>
      </div>
    );
  }

  // Not enabled, mid-enrolment → show secret + confirm.
  if (mode === "enrolling" && secret) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-stone max-w-prose">
          Añade esta clave a tu app de autenticación (Google Authenticator, Authy,
          1Password…) y luego introduce el código de 6 dígitos para confirmar.
        </p>
        <div className="rounded-card border border-hairline bg-field p-3 flex items-center justify-between gap-3">
          <code className="text-sm text-ink break-all font-mono tracking-wider">{secret}</code>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              navigator.clipboard
                ?.writeText(secret)
                .then(() => toast.success("Clave copiada"))
                .catch(() => toast.error("No se pudo copiar"));
            }}
          >
            Copiar
          </Button>
        </div>
        {uri && (
          <a
            href={uri}
            className="inline-block text-xs text-nova-ink underline underline-offset-2"
          >
            Abrir en mi app de autenticación
          </a>
        )}
        <div className="space-y-2">
          {CodeInput}
          <div className="flex gap-2">
            <Button variant="cta" onClick={confirm} loading={busy} disabled={code.length < 6}>
              Confirmar y activar
            </Button>
            <Button variant="ghost" onClick={reset} disabled={busy}>
              Cancelar
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Not enabled, idle.
  return (
    <div className="flex items-center justify-between gap-4 flex-wrap">
      <p className="text-sm text-stone max-w-prose">
        Añade una capa extra de seguridad: además de tu contraseña, pediremos un código
        de un solo uso de tu app de autenticación.
      </p>
      <Button variant="cta" onClick={startEnroll} loading={busy}>
        Activar 2FA
      </Button>
    </div>
  );
}

function ByokCard({ isPro }: { isPro: boolean }) {
  const qc = useQueryClient();
  const status = useQuery({
    queryKey: ["llm-key"],
    queryFn: () => account.llmKey.get(),
    enabled: isPro,
  });
  const [provider, setProvider] = useState("anthropic");
  const [key, setKey] = useState("");

  const save = useMutation({
    mutationFn: () => account.llmKey.set(provider, key),
    onSuccess: (s) => {
      qc.setQueryData(["llm-key"], s);
      setKey("");
      toast.success("Clave guardada", "Tus chats con el agente usarán tu clave.");
    },
    onError: (e) => toast.error("No pudimos guardar la clave", (e as Error).message),
  });
  const clear = useMutation({
    mutationFn: () => account.llmKey.clear(),
    onSuccess: (s) => {
      qc.setQueryData(["llm-key"], s);
      toast.success("Clave eliminada", "Volvemos a la clave de la plataforma.");
    },
    onError: (e) => toast.error("No pudimos eliminar la clave", (e as Error).message),
  });

  if (!isPro) {
    return (
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <p className="text-sm text-stone max-w-prose">
          Usa tu propia clave de Anthropic u OpenAI para que tus conversaciones con el
          agente corran con tu cuenta y tu cuota. Disponible en el plan PRO.
        </p>
        <Button variant="outline" onClick={() => (window.location.hash = "#/billing")}>
          Ver PRO
        </Button>
      </div>
    );
  }

  if (status.data?.configured) {
    return (
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <p className="text-sm text-stone max-w-prose">
          Clave <span className="text-ink font-medium capitalize">{status.data.provider}</span>{" "}
          configurada. Tus chats con el agente la usan. La clave se guarda cifrada y
          nunca se muestra.
        </p>
        <Button variant="outline" onClick={() => clear.mutate()} loading={clear.isPending}>
          Eliminar clave
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-stone max-w-prose">
        Pega tu clave de API. Se guarda cifrada y nunca se muestra de vuelta.
      </p>
      <div className="flex flex-wrap items-end gap-2">
        <label className="text-xs text-stone flex flex-col gap-1">
          Proveedor
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="h-10 rounded-btn border border-hairline bg-field px-3 text-sm text-ink"
          >
            <option value="anthropic">Anthropic</option>
            <option value="openai">OpenAI</option>
          </select>
        </label>
        <Input
          type="password"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="sk-…"
          autoComplete="off"
          className="flex-1 min-w-[220px]"
        />
        <Button
          variant="cta"
          onClick={() => save.mutate()}
          loading={save.isPending}
          disabled={key.trim().length < 20}
        >
          Guardar
        </Button>
      </div>
    </div>
  );
}
