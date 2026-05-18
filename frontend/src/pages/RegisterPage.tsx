import { useState } from "react";
import { useTranslation } from "react-i18next";
import { auth } from "@/shared/api";

export function RegisterPage() {
  const { t, i18n } = useTranslation();
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
      setVerificationLink(r.verification_link ?? null);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  if (verificationLink !== null) {
    return (
      <div className="max-w-sm mx-auto py-12 px-4">
        <h1 className="text-2xl font-bold mb-3">{t("auth.verify")}</h1>
        <p className="text-sm text-gray-600 mb-4">{t("auth.verifyHint")}</p>
        {verificationLink && (
          <a className="btn-primary w-full mb-3" href={verificationLink}>
            Verificar ahora (dev)
          </a>
        )}
        <a href="#/login" className="btn-secondary w-full">{t("auth.login")}</a>
      </div>
    );
  }

  return (
    <div className="max-w-sm mx-auto py-12 px-4">
      <h1 className="text-2xl font-bold mb-6">{t("auth.register")}</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="label" htmlFor="display_name">Nombre</label>
          <input id="display_name" className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} autoComplete="name" />
        </div>
        <div>
          <label className="label" htmlFor="email">{t("auth.email")}</label>
          <input id="email" type="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
        </div>
        <div>
          <label className="label" htmlFor="password">{t("auth.password")} (min 10)</label>
          <input id="password" type="password" minLength={10} className="input" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="new-password" />
        </div>
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? t("common.loading") : t("auth.registerCta")}
        </button>
        <p className="text-sm text-gray-600 text-center">
          {t("auth.haveAccount")} <a href="#/login" className="text-brand-600 hover:underline">{t("auth.login")}</a>
        </p>
      </form>
    </div>
  );
}
