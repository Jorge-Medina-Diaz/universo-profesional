import { useState } from "react";
import { useTranslation } from "react-i18next";
import { auth, useAuthStore } from "@/shared/api";

export function LoginPage() {
  const { t } = useTranslation();
  const setTokens = useAuthStore((s) => s.setTokens);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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
      window.location.hash = "#/universe";
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-sm mx-auto py-12 px-4">
      <h1 className="text-2xl font-bold mb-6">{t("auth.login")}</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="label" htmlFor="email">{t("auth.email")}</label>
          <input id="email" type="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
        </div>
        <div>
          <label className="label" htmlFor="password">{t("auth.password")}</label>
          <input id="password" type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
        </div>
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? t("common.loading") : t("auth.loginCta")}
        </button>
        <div className="text-sm text-gray-600 flex justify-between">
          <a href="#/register" className="hover:underline">{t("auth.noAccount")} →</a>
          <a href="#/auth/verify" className="hover:underline">{t("auth.forgot")}</a>
        </div>
      </form>
    </div>
  );
}
