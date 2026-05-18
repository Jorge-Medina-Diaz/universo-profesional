import { useEffect, useState } from "react";
import { auth } from "@/shared/api";

export function VerifyEmailPage({ token }: { token: string }) {
  const [state, setState] = useState<"idle" | "ok" | "err">("idle");
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
      <div className="max-w-md mx-auto py-12 px-4">
        <h1 className="text-2xl font-bold mb-2">Verificar email</h1>
        <p className="text-gray-600">Falta el token en la URL.</p>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto py-12 px-4">
      <h1 className="text-2xl font-bold mb-3">Verificar email</h1>
      {state === "idle" && <p className="text-gray-600">Verificando…</p>}
      {state === "ok" && (
        <>
          <p className="text-green-700 mb-4">¡Email verificado! Ya puedes iniciar sesión.</p>
          <a href="#/login" className="btn-primary">Iniciar sesión</a>
        </>
      )}
      {state === "err" && (
        <>
          <p className="text-red-600 mb-4">Error: {msg}</p>
          <a href="#/login" className="btn-secondary">Volver</a>
        </>
      )}
    </div>
  );
}
