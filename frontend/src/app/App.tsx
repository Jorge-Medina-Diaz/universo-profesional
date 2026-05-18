import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/shared/api";
import { Router } from "./Router";
import { Layout } from "./Layout";

export function App() {
  const { t } = useTranslation();
  const { accessToken } = useAuthStore();
  return (
    <Layout title={t("app.title")} isAuthed={!!accessToken}>
      <Router />
    </Layout>
  );
}
