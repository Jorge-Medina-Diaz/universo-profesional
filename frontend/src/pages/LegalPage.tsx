/**
 * Minimal public legal page (terms / privacy / cookies). Reachable without
 * auth so the footer links resolve instead of bouncing to the login screen.
 * Content is intentionally short placeholder copy — replace with the final
 * legal text before a public launch.
 */
import { PageHeader } from "@/ui";

type LegalDoc = "terms" | "privacy" | "cookies";

const DOCS: Record<LegalDoc, { eyebrow: string; title: string; body: string[] }> = {
  terms: {
    eyebrow: "Legal",
    title: "Términos del servicio",
    body: [
      "Universo Profesional es una herramienta para construir y mantener tu perfil profesional. Al usarla aceptas un uso responsable del servicio.",
      "Esta es una versión preliminar de los términos. Para cualquier consulta legal, escríbenos a hola@webtools.es.",
    ],
  },
  privacy: {
    eyebrow: "Legal",
    title: "Privacidad",
    body: [
      "Tratamos tus datos para ofrecerte el servicio: construir tu universo profesional, generar documentos y conectar integraciones que tú autorizas.",
      "Puedes exportar o eliminar todos tus datos en cualquier momento desde Ajustes (GDPR Art. 20). Para dudas: hola@webtools.es.",
    ],
  },
  cookies: {
    eyebrow: "Legal",
    title: "Cookies",
    body: [
      "Usamos cookies necesarias para que la app funcione (sesión, preferencias). Las de diagnóstico nos ayudan a corregir errores; las de marketing están desactivadas por defecto.",
      "Puedes ajustar tus preferencias desde el banner de cookies.",
    ],
  },
};

export function LegalPage({ doc }: { doc: string }) {
  const meta = DOCS[(doc as LegalDoc)] ?? DOCS.terms;
  return (
    <div className="max-w-2xl mx-auto px-4 py-16 sm:py-24">
      <PageHeader eyebrow={meta.eyebrow} title={meta.title} />
      <div className="mt-8 space-y-4">
        {meta.body.map((p, i) => (
          <p key={i} className="text-stone leading-relaxed">
            {p}
          </p>
        ))}
      </div>
      <a href="#/" className="inline-flex mt-10 text-sm text-stone hover:text-ink transition-colors">
        ← Volver al inicio
      </a>
    </div>
  );
}
