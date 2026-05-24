import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { auth, useAuthStore } from "@/shared/api";
import { integrations } from "@/shared/api-extra";
import { Button, Card, Field, Input, Reveal, Stagger } from "@/ui";
import { AuthHero } from "./_auth/AuthHero";

export function LoginPage() {
  const { t } = useTranslation();
  const setTokens = useAuthStore((s) => s.setTokens);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [oauthError, setOauthError] = useState<string | null>(null);

  const linkedinProbe = useQuery({
    queryKey: ["linkedin-probe"],
    queryFn: () => integrations.linkedin.oidcAuthorize(),
    staleTime: 60_000,
  });
  const linkedinAvailable = linkedinProbe.data?.configured ?? false;

  useEffect(() => {
    const hash = window.location.hash;
    const q = hash.includes("?") ? hash.split("?")[1] : "";
    const p = new URLSearchParams(q);
    const e = p.get("oauth_error");
    if (e) setOauthError(decodeURIComponent(e));
  }, []);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tokens = await auth.login({ email, password });
      setTokens({
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        userId: tokens.user_id,
        email: tokens.email,
      });
      window.location.hash = "#/";
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

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
          title="Bienvenido de vuelta."
          subtitle="Tu universo profesional te espera. Sigue donde lo dejaste."
        />
      </div>

      <div className="flex items-center justify-center px-4 py-12 md:py-16">
        <div className="w-full max-w-md">
          <Reveal>
            <h1 className="font-display text-[34px] md:text-heading-lg leading-[1.05] text-ink mb-2">
              {t("auth.login")}
            </h1>
            <p className="text-stone mb-8">Entra con tu cuenta para continuar.</p>
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
              {oauthError && (
                <p role="alert" className="text-sm text-red-600 mt-3">
                  LinkedIn sign-in falló: {oauthError}
                </p>
              )}
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
            <Stagger className="space-y-4" delayStep={0.04} initialDelay={linkedinAvailable ? 0.16 : 0.06}>
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
              <Field label={t("auth.password")} required>
                {(p) => (
                  <Input
                    {...p}
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                  />
                )}
              </Field>
              {error && (
                <Card tone="canvas" bordered padding="sm" className="border-red-200 bg-red-50/60">
                  <p role="alert" className="text-sm text-red-700">{error}</p>
                </Card>
              )}
              <Button type="submit" fullWidth size="lg" loading={loading}>
                {loading ? t("common.loading") : t("auth.loginCta")}
              </Button>
              <div className="text-sm flex justify-between pt-2">
                <a href="#/register" className="text-stone hover:text-ink transition-colors">
                  {t("auth.noAccount")} →
                </a>
                <a href="#/auth/verify" className="text-stone hover:text-ink transition-colors">
                  {t("auth.forgot")}
                </a>
              </div>
            </Stagger>
          </form>
        </div>
      </div>
    </div>
  );
}
