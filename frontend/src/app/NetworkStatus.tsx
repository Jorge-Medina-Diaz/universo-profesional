/**
 * Offline detection — shows a toast when the browser loses connectivity and
 * pauses TanStack Query retries while offline.
 */
import { useEffect, useRef } from "react";
import { onlineManager } from "@tanstack/react-query";
import { toast } from "@/ui";

export function NetworkStatus() {
  const offlineToastRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    const onOffline = () => {
      onlineManager.setOnline(false);
      if (!offlineToastRef.current) {
        offlineToastRef.current = toast.show({
          variant: "error",
          title: "Sin conexión",
          description:
            "Algunas funciones pueden no estar disponibles. Reintentaremos automáticamente cuando vuelvas a tener red.",
          duration: 0,
        });
      }
    };

    const onOnline = () => {
      onlineManager.setOnline(true);
      if (offlineToastRef.current) {
        toast.dismiss(offlineToastRef.current);
        offlineToastRef.current = undefined;
      }
      toast.success("Conexión restaurada", "Todo vuelve a funcionar con normalidad.");
    };

    window.addEventListener("offline", onOffline);
    window.addEventListener("online", onOnline);

    // Initialise state in case we mount while already offline.
    if (!navigator.onLine) {
      onlineManager.setOnline(false);
      onOffline();
    }

    return () => {
      window.removeEventListener("offline", onOffline);
      window.removeEventListener("online", onOnline);
    };
  }, []);

  return null;
}
