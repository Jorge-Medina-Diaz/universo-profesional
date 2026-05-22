import { useEffect, useState } from "react";
import { CheckCircle2, AlertTriangle, Loader2, MailQuestion } from "lucide-react";
import { auth } from "@/shared/api";
import { Button, Card, Reveal } from "@/ui";

type State = "idle" | "ok" | "err";

export function VerifyEmailPage({ token }: { token: string }) {
  const [state, setState] = useState<State>("idle");
  const [msg, setMsg] = useState<string>("");

  useEffect(() => {
    if (!token) return;
    auth
      .verify(token)
      .then(() => setState("ok"))
      .catch((e: Error) => {
        setState("err");
        setMsg(e.message);
      });
  }, [token]);

  if (!token) {
    return (
      <Centered>
        <Card padding="lg" className="text-center space-y-3 max-w-md">
          <Avatar tone="amber">
            <MailQuestion size={20} />
          </Avatar>
          <h1 className="text-heading-sm font-medium tracking-tight">
            Verificar email
          </h1>
          <p className="text-stone text-sm">Falta el token en la URL.</p>
        </Card>
      </Centered>
    );
  }

  return (
    <Centered>
      <Reveal>
        <Card padding="lg" className="text-center space-y-4 max-w-md">
          {state === "idle" && (
            <>
              <Avatar tone="leaf">
                <Loader2 size={20} className="animate-spin" />
              </Avatar>
              <h1 className="text-heading-sm font-medium tracking-tight">Verificando…</h1>
              <p className="text-stone text-sm">Esto suele tardar menos de un segundo.</p>
            </>
          )}
          {state === "ok" && (
            <>
              <Avatar tone="leaf">
                <CheckCircle2 size={20} />
              </Avatar>
              <h1 className="text-heading-sm font-medium tracking-tight">
                ¡Email verificado!
              </h1>
              <p className="text-stone text-sm">Ya puedes iniciar sesión.</p>
              <div className="pt-2">
                <Button fullWidth onClick={() => (window.location.hash = "#/login")}>
                  Iniciar sesión
                </Button>
              </div>
            </>
          )}
          {state === "err" && (
            <>
              <Avatar tone="red">
                <AlertTriangle size={20} />
              </Avatar>
              <h1 className="text-heading-sm font-medium tracking-tight text-red-700">
                No pudimos verificar tu email
              </h1>
              <p className="text-stone text-sm">{msg}</p>
              <div className="pt-2">
                <Button
                  variant="outline"
                  fullWidth
                  onClick={() => (window.location.hash = "#/login")}
                >
                  Volver
                </Button>
              </div>
            </>
          )}
        </Card>
      </Reveal>
    </Centered>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-[calc(100vh-8rem)] flex items-center justify-center px-4 py-12">
      {children}
    </div>
  );
}

function Avatar({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "leaf" | "amber" | "red";
}) {
  const cls =
    tone === "leaf"
      ? "bg-leaf-soft text-leaf-ink"
      : tone === "amber"
        ? "bg-sunbeam-soft text-sunbeam-ink"
        : "bg-red-50 text-red-700";
  return (
    <span
      aria-hidden
      className={`inline-flex items-center justify-center w-14 h-14 rounded-full mx-auto ${cls}`}
    >
      {children}
    </span>
  );
}
