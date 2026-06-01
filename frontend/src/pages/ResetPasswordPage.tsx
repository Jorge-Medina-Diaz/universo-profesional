/**
 * Password-reset flow pages.
 *
 * ForgotPasswordPage (#/auth/forgot) — request a reset email.
 * ResetPasswordPage  (#/auth/reset?token=…) — the email link target; set a new
 * password. The backend reset email now points here (with the #/ hash prefix).
 */
import { useState } from "react";
import { CheckCircle2, MailCheck } from "lucide-react";
import { auth } from "@/shared/api";
import { Button, Card, Field, Input, Reveal } from "@/ui";

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-[calc(100vh-8rem)] flex items-center justify-center px-4 py-12">
      {children}
    </div>
  );
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await auth.requestPasswordReset(email);
      setSent(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <Centered>
        <Reveal>
          <Card padding="lg" className="max-w-md w-full text-center space-y-3">
            <span
              aria-hidden
              className="inline-flex items-center justify-center w-14 h-14 rounded-full mx-auto bg-leaf-soft text-leaf-ink"
            >
              <MailCheck size={20} />
            </span>
            <h1 className="font-display text-heading-sm text-ink">Revisa tu email</h1>
            <p className="text-sm text-stone">
              Si existe una cuenta con <span className="text-ink">{email}</span>, te hemos
              enviado un enlace para restablecer tu contraseña.
            </p>
            <Button
              variant="outline"
              fullWidth
              onClick={() => (window.location.hash = "#/login")}
            >
              Volver a iniciar sesión
            </Button>
          </Card>
        </Reveal>
      </Centered>
    );
  }

  return (
    <Centered>
      <Reveal>
        <Card padding="lg" className="max-w-md w-full space-y-4">
          <h1 className="font-display text-heading-sm text-ink">Restablecer contraseña</h1>
          <p className="text-sm text-stone">
            Introduce tu email y te enviaremos un enlace para crear una contraseña nueva.
          </p>
          <form onSubmit={onSubmit} className="space-y-4">
            <Field label="Email" required>
              {(p) => (
                <Input
                  {...p}
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  placeholder="tu@email.com"
                />
              )}
            </Field>
            {error && (
              <p role="alert" className="text-sm text-danger">
                {error}
              </p>
            )}
            <Button type="submit" variant="cta" fullWidth size="lg" loading={loading}>
              Enviar enlace
            </Button>
            <a
              href="#/login"
              className="block text-center text-sm text-stone hover:text-ink transition-colors"
            >
              ← Volver
            </a>
          </form>
        </Card>
      </Reveal>
    </Centered>
  );
}

export function ResetPasswordPage({ token }: { token: string }) {
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await auth.confirmPasswordReset(token, password);
      setDone(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <Centered>
        <Card padding="lg" className="max-w-md w-full text-center space-y-3">
          <h1 className="font-display text-heading-sm text-ink">Enlace no válido</h1>
          <p className="text-sm text-stone">Falta el token en la URL.</p>
          <Button
            variant="outline"
            fullWidth
            onClick={() => (window.location.hash = "#/auth/forgot")}
          >
            Pedir un enlace nuevo
          </Button>
        </Card>
      </Centered>
    );
  }

  if (done) {
    return (
      <Centered>
        <Reveal>
          <Card padding="lg" className="max-w-md w-full text-center space-y-3">
            <span
              aria-hidden
              className="inline-flex items-center justify-center w-14 h-14 rounded-full mx-auto bg-leaf-soft text-leaf-ink"
            >
              <CheckCircle2 size={20} />
            </span>
            <h1 className="font-display text-heading-sm text-ink">Contraseña actualizada</h1>
            <p className="text-sm text-stone">Ya puedes iniciar sesión con tu nueva contraseña.</p>
            <Button fullWidth onClick={() => (window.location.hash = "#/login")}>
              Iniciar sesión
            </Button>
          </Card>
        </Reveal>
      </Centered>
    );
  }

  return (
    <Centered>
      <Reveal>
        <Card padding="lg" className="max-w-md w-full space-y-4">
          <h1 className="font-display text-heading-sm text-ink">Nueva contraseña</h1>
          <p className="text-sm text-stone">Elige una contraseña nueva para tu cuenta.</p>
          <form onSubmit={onSubmit} className="space-y-4">
            <Field label="Nueva contraseña (mín. 10)" required>
              {(p) => (
                <Input
                  {...p}
                  type="password"
                  minLength={10}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                />
              )}
            </Field>
            {error && (
              <p role="alert" className="text-sm text-danger">
                {error}
              </p>
            )}
            <Button
              type="submit"
              variant="cta"
              fullWidth
              size="lg"
              loading={loading}
              disabled={password.length < 10}
            >
              Cambiar contraseña
            </Button>
          </form>
        </Card>
      </Reveal>
    </Centered>
  );
}
