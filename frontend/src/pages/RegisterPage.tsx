import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { auth, useAuthStore } from "@/shared/api";
import { integrations } from "@/shared/api-extra";
import { Button, Card, Field, Input, Reveal, Stagger } from "@/ui";
import { AuthHero } from "./_auth/AuthHero";

export function RegisterPage() {
  const { t, i18n } = useTranslation();
  const setTokens = useAuthStore((s) => s.setTokens);
  const linkedinProbe = useQuery({
    queryKey: ["linkedin-probe"],
    queryFn: () => integrations.linkedin.oidcAuthorize(),
    staleTime: 60_000,
  });
  const linkedinAvailable = linkedinProbe.data?.configured ?? false;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [verificationLink, setVerificationLink] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const r = await auth.register({
        email,
        password,
        display_name: displayName || undefined,
        locale: i18n.resolvedLanguage === "en" ? "en-US" : "es-ES",
      });
      try {
        const tokens = await auth.login({ email, password });
        setTokens({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          userId: tokens.user_id,
          email: tokens.email,
        });
        window.location.hash = "#/";
        return;
      } catch {
        setVerificationLink(r.verification_link ?? null);
      }
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  if (verificationLink !== null) {
    return (
      <div className="max-w-md mx-auto py-16 px-4">
        <Reveal>
          <Card padding="lg" tone="surface" className="space-y-4">
            <h1 className="text-heading-sm font-medium tracking-tight">{t("auth.verify")}</h1>
            <p className="text-sm text-stone">{t("auth.verifyHint")}</p>
            <div className="flex flex-col gap-2 pt-2">
              {verificationLink && (
                <Button fullWidth size="lg" onClick={() => (window.location.href = verificationLink)}>
                  Verificar ahora (dev)
                </Button>
              )}
              <Button
                variant="outline"
                fullWidth
                size="lg"
                onClick={() => (window.location.hash = "#/login")}
              >
                {t("auth.login")}
              </Button>
            </div>
          </Card>
        </Reveal>
      </div>
    );
  }

  const onLinkedIn = async () => {
    try {
      const r = await integrations.linkedin.oidcAuthorize();
      window.location.href = r.authorize_url;
    } catch (e: unknown) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] grid lg:grid-cols-2 bg-canvas">
      <div className="hidden lg:block bg-surface">
        <AuthHero
          title="Tu carrera, un universo vivo."
          subtitle="Crea tu cuenta y empieza a hablar con tu agente personal en segundos."
        />
      </div>

      <div className="flex items-center justify-center px-4 py-12 md:py-16">
        <div className="w-full max-w-md">
          <Reveal>
            <h1 className="text-heading md:text-[34px] font-medium tracking-tight text-ink mb-2">
              {t("auth.register")}
            </h1>
            <p className="text-stone mb-8">
              Sin tarjeta. En menos de 5 minutos tendrás tu universo montado.
            </p>
          </Reveal>

          {linkedinAvailable && (
            <Reveal delay={0.06}>
              <button
                type="button"
                onClick={onLinkedIn}
                className="w-full h-12 rounded-btn bg-[#0a66c2] hover:bg-[#004182] text-white font-medium text-sm transition-colors duration-180 inline-flex items-center justify-center gap-2"
              >
                <span aria-hidden className="text-base font-bold">in</span>
                Continuar con LinkedIn
              </button>
              <p className="text-xs text-stone text-center mt-2">
                Sin contraseña. Tu universo arranca con tu LinkedIn ya sincronizado.
              </p>
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center" aria-hidden>
                  <div className="w-full border-t border-ink/10" />
                </div>
                <div className="relative flex justify-center">
                  <span className="bg-canvas px-3 text-xs text-stone uppercase tracking-wider">
                    o con email
                  </span>
                </div>
              </div>
            </Reveal>
          )}

          <form onSubmit={onSubmit}>
            <Stagger
              className="space-y-4"
              delayStep={0.04}
              initialDelay={linkedinAvailable ? 0.16 : 0.06}
            >
              <Field label="Nombre" hint="Cómo quieres que te llame el agente">
                {(p) => (
                  <Input
                    {...p}
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    autoComplete="name"
                    placeholder="Tu nombre"
                  />
                )}
              </Field>
              <Field label={t("auth.email")} required>
                {(p) => (
                  <Input
                    {...p}
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    placeholder="tu@email.com"
                  />
                )}
              </Field>
              <Field label={`${t("auth.password")} (mín. 10)`} required>
                {(p) => (
                  <Input
                    {...p}
                    type="password"
                    minLength={10}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                  />
                )}
              </Field>
              {error && (
                <Card tone="canvas" bordered padding="sm" className="border-red-200 bg-red-50/60">
                  <p role="alert" className="text-sm text-red-700">{error}</p>
                </Card>
              )}
              <Button type="submit" fullWidth size="lg" loading={loading}>
                {loading ? t("common.loading") : t("auth.registerCta")}
              </Button>
              <p className="text-sm text-stone text-center pt-2">
                {t("auth.haveAccount")}{" "}
                <a href="#/login" className="text-ink underline-offset-2 hover:underline">
                  {t("auth.login")}
                </a>
              </p>
            </Stagger>
          </form>
        </div>
      </div>
    </div>
  );
}
