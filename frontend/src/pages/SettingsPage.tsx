import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { auth, useAuthStore } from "@/shared/api";

export function SettingsPage() {
  const { t } = useTranslation();
  const me = useQuery({ queryKey: ["me"], queryFn: () => auth.me() });
  const clear = useAuthStore((s) => s.clear);

  const exportData = async () => {
    const { accessToken } = useAuthStore.getState();
    const resp = await fetch("/api/v1/users/me/export", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!resp.ok) return alert("Error");
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `cvs-saas-export.zip`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const deleteAccount = async () => {
    if (!confirm(t("settings.deleteConfirm"))) return;
    await auth.deleteMe();
    clear();
    window.location.hash = "#/";
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 space-y-6">
      <h1 className="text-2xl font-bold">{t("settings.title")}</h1>

      <section className="card">
        <h2 className="font-semibold mb-2">Cuenta</h2>
        {me.data && (
          <dl className="text-sm grid grid-cols-3 gap-y-2">
            <dt className="text-gray-500">Email</dt>
            <dd className="col-span-2">{me.data.email}</dd>
            <dt className="text-gray-500">Nombre</dt>
            <dd className="col-span-2">{me.data.display_name ?? "—"}</dd>
            <dt className="text-gray-500">Locale</dt>
            <dd className="col-span-2">{me.data.locale}</dd>
            <dt className="text-gray-500">Email verificado</dt>
            <dd className="col-span-2">{me.data.email_verified ? "Sí" : "No"}</dd>
            <dt className="text-gray-500">MFA</dt>
            <dd className="col-span-2">{me.data.mfa_enabled ? "Activo" : "Desactivado"}</dd>
            <dt className="text-gray-500">Cuenta desde</dt>
            <dd className="col-span-2">{new Date(me.data.created_at).toLocaleString()}</dd>
          </dl>
        )}
      </section>

      <section className="card">
        <h2 className="font-semibold mb-2">RGPD</h2>
        <p className="text-sm text-gray-600 mb-3">
          Descarga todos tus datos en un archivo ZIP. Cumple Art. 20 (portabilidad).
        </p>
        <button onClick={exportData} className="btn-primary">{t("settings.exportRgpd")}</button>
      </section>

      <section className="card border-red-200">
        <h2 className="font-semibold mb-2 text-red-700">Zona peligrosa</h2>
        <p className="text-sm text-gray-600 mb-3">
          La cuenta se marca como borrada inmediatamente. Tras 30 días se elimina
          físicamente (Art. 17 RGPD: derecho al olvido).
        </p>
        <button onClick={deleteAccount} className="btn-danger">{t("settings.deleteAccount")}</button>
      </section>
    </div>
  );
}
