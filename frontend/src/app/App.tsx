import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/shared/api";
import { Router } from "./Router";
import { Layout } from "./Layout";
import { CopilotProvider } from "./CopilotProvider";
import { ChatPanel } from "@/chat/ChatPanel";
import { BottomNav } from "@/widgets/BottomNav";

export function App() {
  const { t } = useTranslation();
  const { accessToken } = useAuthStore();
  return (
    <CopilotProvider>
      <Layout title={t("app.title")} isAuthed={!!accessToken}>
        <Router />
        {accessToken && (
          <>
            <BottomNav />
            <ChatPanel />
          </>
        )}
      </Layout>
    </CopilotProvider>
  );
}
