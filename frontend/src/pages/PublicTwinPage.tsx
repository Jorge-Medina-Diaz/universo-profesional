import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";

import { TwinChatCard } from "@/landing/components/TwinChatCard";
import { publicTwin, type PublicTwinProfile } from "@/shared/api";

/** Public twin surface (#/t/{slug}) — works logged-out, chrome-less.
 *  `?embed=1` strips it to the chat card for portfolio iframes. */
export function PublicTwinPage({ slug, embed }: { slug: string; embed: boolean }) {
  const profile = useQuery({
    queryKey: ["public-twin", slug],
    queryFn: () => publicTwin.profile(slug),
    retry: false,
    staleTime: 5 * 60_000,
  });

  if (profile.isLoading) {
    return (
      <div className="min-h-screen grid place-items-center text-stone text-sm">
        Cargando perfil…
      </div>
    );
  }
  if (profile.isError || !profile.data) {
    return (
      <div className="min-h-screen grid place-items-center px-6 text-center">
        <div>
          <p className="text-ink font-medium mb-1">Perfil no disponible</p>
          <p className="text-sm text-stone">
            Este enlace no existe o su propietario lo ha desactivado.
          </p>
        </div>
      </div>
    );
  }
  return <TwinSurface slug={slug} profile={profile.data} embed={embed} />;
}

function TwinSurface({
  slug,
  profile,
  embed,
}: {
  slug: string;
  profile: PublicTwinProfile;
  embed: boolean;
}) {
  const [showLead, setShowLead] = useState(false);

  const chat = (
    <TwinChatCard
      slug={slug}
      suggested={profile.suggested_questions}
      height={embed ? "h-[340px]" : "h-[420px]"}
    />
  );

  const leadCard = showLead ? (
    <LeadForm slug={slug} onDone={() => setShowLead(false)} />
  ) : (
    <button
      type="button"
      onClick={() => setShowLead(true)}
      className="text-xs text-stone hover:text-ink underline underline-offset-2 transition-colors"
    >
      ¿Prefieres hablar en persona? Deja tu contacto
    </button>
  );

  if (embed) {
    return (
      <div className="p-3 flex flex-col gap-2 bg-canvas min-h-screen">
        <p className="text-xs text-stone px-1">
          <Sparkles size={11} className="inline mr-1 -mt-0.5" aria-hidden />
          Gemelo digital de <span className="text-ink">{profile.display_name}</span>
        </p>
        {chat}
        <div className="px-1 flex items-center justify-between gap-2">
          {leadCard}
          <p className="text-[10px] text-stone/80">IA · Universo Profesional</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen constellation-bg">
      <div className="mx-auto max-w-2xl px-4 py-10 flex flex-col gap-6">
        <header className="text-center">
          <p className="text-xs uppercase tracking-widest text-stone mb-2">
            Gemelo digital profesional
          </p>
          <h1 className="font-display text-3xl text-ink">{profile.display_name}</h1>
          {profile.headline && <p className="text-stone mt-1">{profile.headline}</p>}
          {Object.keys(profile.kind_counts).length > 0 && (
            <div className="flex flex-wrap gap-2 justify-center mt-3">
              {Object.entries(profile.kind_counts).map(([k, n]) => (
                <span
                  key={k}
                  className="text-[11px] px-2.5 py-1 rounded-full bg-surface border border-hairline text-stone"
                >
                  {n} {KIND_LABELS[k] ?? k}
                </span>
              ))}
            </div>
          )}
        </header>
        {chat}
        <div className="flex flex-col items-center gap-3">
          {leadCard}
          <p className="text-[11px] text-stone/80 text-center max-w-md">{profile.disclosure}</p>
        </div>
      </div>
    </div>
  );
}

const KIND_LABELS: Record<string, string> = {
  experience: "experiencias",
  education: "formación",
  skill: "habilidades",
  project: "proyectos",
  certification: "certificaciones",
  language: "idiomas",
  achievement: "logros",
};

function LeadForm({ slug, onDone }: { slug: string; onDone: () => void }) {
  const [contact, setContact] = useState("");
  const [message, setMessage] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");

  if (state === "sent") {
    return (
      <p className="text-sm text-leaf" role="status">
        Mensaje enviado. Te responderá en persona.
      </p>
    );
  }
  return (
    <form
      className="w-full max-w-sm flex flex-col gap-2 rounded-xl border border-hairline bg-surface/60 p-3"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!contact.trim()) return;
        setState("sending");
        try {
          await publicTwin.lead(slug, {
            contact: contact.trim(),
            message: message.trim() || undefined,
          });
          setState("sent");
          setTimeout(onDone, 4000);
        } catch {
          setState("error");
        }
      }}
    >
      <p className="text-xs text-stone">Deja tu email o teléfono y el propietario te contactará.</p>
      <input
        value={contact}
        onChange={(e) => setContact(e.target.value)}
        placeholder="tu@email.com"
        maxLength={200}
        required
        aria-label="Tu contacto"
        className="h-9 px-3 rounded-lg bg-canvas border border-hairline text-sm text-ink placeholder:text-stone outline-none focus:border-nova/50"
      />
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Mensaje (opcional)"
        maxLength={1000}
        rows={2}
        aria-label="Mensaje"
        className="px-3 py-2 rounded-lg bg-canvas border border-hairline text-sm text-ink placeholder:text-stone outline-none focus:border-nova/50 resize-none"
      />
      {state === "error" && (
        <p className="text-xs text-danger" role="alert">
          No se pudo enviar. Inténtalo de nuevo.
        </p>
      )}
      <button
        type="submit"
        disabled={state === "sending" || !contact.trim()}
        className="h-9 rounded-lg bg-nova text-white text-sm disabled:opacity-40"
      >
        {state === "sending" ? "Enviando…" : "Enviar"}
      </button>
    </form>
  );
}

export default PublicTwinPage;
