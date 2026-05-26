import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/shared/api";
import { Router } from "./Router";
import { Layout } from "./Layout";
import { CopilotProvider } from "./CopilotProvider";
import { ErrorBoundary } from "./ErrorBoundary";
import { CommandPalette } from "./CommandPalette";
import { ShortcutsOverlay } from "./ShortcutsOverlay";
import { NetworkStatus } from "./NetworkStatus";
import { ToasterProvider } from "@/ui";
import { TourProvider } from "./tour/TourProvider";

/**
 * Sprint 4 layout: chat lives in `HomePage` (the `/` route), not as a
 * floating sidebar/FAB. App keeps the Layout shell (top nav + container)
 * around every page; the universe is reachable from the in-chat drawer.
 */
export function App() {
  const { t } = useTranslation();
  const { accessToken } = useAuthStore();
  return (
    <ErrorBoundary>
      <ToasterProvider>
        <TourProvider>
          <CopilotProvider>
            <NetworkStatus />
            <Layout title={t("app.title")} isAuthed={!!accessToken}>
              <ErrorBoundary>
                <Router />
              </ErrorBoundary>
            </Layout>
            {!!accessToken && (
              <>
                <CommandPalette />
                <ShortcutsOverlay />
              </>
            )}
          </CopilotProvider>
        </TourProvider>
      </ToasterProvider>
    </ErrorBoundary>
  );
}
