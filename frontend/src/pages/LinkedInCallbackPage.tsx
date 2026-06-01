/**
 * Lands here after the LinkedIn OIDC backend callback redirects with
 * tokens stuffed into the URL fragment. We extract them, hydrate Zustand,
 * and bounce to /universe (or /connections if the user was linking an
 * existing account).
 *
 * Fragment-based token transfer keeps secrets off the server access logs —
 * the SPA fetches and clears them immediately on mount.
 */
import { useEffect, useState } from "react";
import { AlertTriangle, Sparkles } from "lucide-react";
import { motion } from "motion/react";
import { useAuthStore } from "@/shared/api";
import { Button, Card, Reveal } from "@/ui";
import { LinkedInIcon } from "@/ui/icons";

export function LinkedInCallbackPage() {
  const setTokens = useAuthStore((s) => s.setTokens);
  const [error, setError] = useState<string | null>(null);
  const [createdNew, setCreatedNew] = useState(false);

  useEffect(() => {
    const hash = window.location.hash;
    const queryStart = hash.indexOf("?");
    if (queryStart === -1) {
      setError("Sin parámetros en el callback");
      return;
    }
    const params = new URLSearchParams(hash.slice(queryStart + 1));
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    const userId = params.get("user_id");
    const email = params.get("email");
    const created = params.get("created") === "1";
    const linked = params.get("linked") === "1";

    if (!accessToken || !refreshToken || !userId || !email) {
      setError("Tokens incompletos en el callback");
      return;
    }
    setTokens({ accessToken, refreshToken, userId, email });
    setCreatedNew(created);

    setTimeout(() => {
      if (created) {
        window.location.hash = "#/onboarding/chat";
      } else if (linked) {
        window.location.hash = "#/connections?connected=linkedin_oidc";
      } else {
        window.location.hash = "#/universe";
      }
    }, 600);
  }, [setTokens]);

  return (
    <div className="min-h-[calc(100vh-8rem)] flex items-center justify-center px-4 py-12">
      <Reveal>
        <Card padding="lg" className="text-center space-y-4 max-w-md">
          {error ? (
            <>
              <span
                aria-hidden
                className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-danger-soft text-danger-ink mx-auto"
              >
                <AlertTriangle size={20} />
              </span>
              <h1 className="text-heading-sm font-medium tracking-tight text-danger-ink">
                Algo falló
              </h1>
              <p className="text-stone text-sm">{error}</p>
              <div className="pt-2">
                <Button
                  fullWidth
                  variant="outline"
                  onClick={() => (window.location.hash = "#/login")}
                >
                  Volver al login
                </Button>
              </div>
            </>
          ) : (
            <>
              <motion.span
                aria-hidden
                animate={{ scale: [1, 1.06, 1] }}
                transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
                className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-[#0a66c2] text-white mx-auto"
              >
                <LinkedInIcon size={24} />
              </motion.span>
              <h1 className="text-heading-sm font-medium tracking-tight inline-flex items-center justify-center gap-2">
                {createdNew ? "¡Bienvenida/o!" : "Iniciando sesión"}
                <Sparkles size={16} className="text-sunbeam-ink" />
              </h1>
              <p className="text-stone text-sm">
                {createdNew
                  ? "Preparando tu universo profesional..."
                  : "Te llevamos a tu universo en un instante."}
              </p>
            </>
          )}
        </Card>
      </Reveal>
    </div>
  );
}
