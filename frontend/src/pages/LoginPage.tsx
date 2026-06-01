import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { auth, universe, useAuthStore } from "@/shared/api";
import { integrations } from "@/shared/api-extra";
import { Button, Card, Field, Input, Reveal, Stagger } from "@/ui";
import { AuthHero } from "./_auth/AuthHero";
import { queryKeys } from "@/shared/queryKeys";
import { isOnboardingComplete } from "@/shared/onboarding";

export function LoginPage() {
  const { t } = useTranslation();
  const setTokens = useAuthStore((s) => s.setTokens);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [oauthError, setOauthError] = useState<string | null>(null);
  // MFA second step: set once the password is accepted but a TOTP code is required.
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState("");

  const linkedinProbe = useQuery({
    queryKey: queryKeys.linkedin.probe,
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

  const finishLogin = async (tokens: {
    access_token: string;
    refresh_token: string;
    user_id: string;
    email: string;
  }) => {
    setTokens({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      userId: tokens.user_id,
      email: tokens.email,
    });

    // Route new users (empty universe) straight to onboarding — but only if
    // they haven't already been through it, so returning users who skipped
    // onboarding aren't funnelled back every login.
    let target = "#/";
    try {
      const [summary, me] = await Promise.all([
        universe.summary(),
        auth.me().catch(() => null),
      ]);
      const hasData =
        summary.counts?.experiences > 0 ||
        summary.counts?.educations > 0 ||
        summary.counts?.skills > 0;
      if (
        !hasData &&
        !isOnboardingComplete(tokens.user_id, me?.onboarding_completed_at)
      ) {
        target = "#/onboarding";
      }
    } catch {
      /* ignore, default to home */
    }
    window.location.hash = target;
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tokens = await auth.login({ email, password });
      if (tokens.mfa_required && tokens.mfa_token) {
        // Password OK, but a second factor is required — show the code step.
        setMfaToken(tokens.mfa_token);
        setLoading(false);
        return;
      }
      await finishLogin(tokens);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const onSubmitMfa = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mfaToken) return;
    setError(null);
    setLoading(true);
    try {
      const tokens = await auth.mfaLogin({ mfa_token: mfaToken, code: mfaCode });
      await finishLogin(tokens);
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
            <p className="text-stone mb-8">
              {mfaToken
                ? "Verificación en dos pasos: introduce el código de tu app de autenticación."
                : "Entra con tu cuenta para continuar."}
            </p>
          </Reveal>

          {mfaToken ? (
            <form onSubmit={onSubmitMfa}>
              <Stagger className="space-y-4" delayStep={0.04} initialDelay={0.06}>
                <Field label="Código de verificación" required>
                  {(p) => (
                    <Input
                      {...p}
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      pattern="[0-9]*"
                      maxLength={6}
                      value={mfaCode}
                      onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ""))}
                      placeholder="123456"
                      autoFocus
                      required
                    />
                  )}
                </Field>
                {error && (
                  <Card tone="canvas" bordered padding="sm" className="border-red-200 bg-red-50/60">
                    <p role="alert" className="text-sm text-red-700">{error}</p>
                  </Card>
                )}
                <Button
                  type="submit"
                  variant="cta"
                  fullWidth
                  size="lg"
                  loading={loading}
                  disabled={mfaCode.length < 6}
                >
                  {loading ? t("common.loading") : "Verificar"}
                </Button>
                <div className="text-sm flex justify-between pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setMfaToken(null);
                      setMfaCode("");
                      setError(null);
                    }}
                    className="text-stone hover:text-ink transition-colors"
                  >
                    ← Volver
                  </button>
                </div>
              </Stagger>
            </form>
          ) : (
          <>
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
              <Button type="submit" variant="cta" fullWidth size="lg" loading={loading}>
                {loading ? t("common.loading") : t("auth.loginCta")}
              </Button>
              <div className="text-sm flex justify-between pt-2">
                <a href="#/register" className="text-stone hover:text-ink transition-colors">
                  {t("auth.noAccount")} →
                </a>
                <a
                  href="#/auth/forgot"
                  className="text-stone hover:text-ink transition-colors"
                >
                  ¿Olvidaste tu contraseña?
                </a>
              </div>
            </Stagger>
          </form>
          </>
          )}
        </div>
      </div>
    </div>
  );
}
