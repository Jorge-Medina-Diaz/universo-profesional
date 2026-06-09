/**
 * Conversational onboarding — replaces the rigid 7-step wizard.
 *
 * Chat is the primary surface; the shortcut tiles offer the high-leverage
 * import paths up top (GitHub / LinkedIn / PDF).
 */
import { Suspense, lazy, useEffect } from "react";
import { FileText, ArrowRight, Sparkles } from "lucide-react";
import { GitHubIcon } from "@/ui/icons";
import { Button, Card, PageHeader, Reveal, Skeleton, Stagger, Surface } from "@/ui";
import { enableCopilot, useCopilotReady } from "@/app/CopilotProvider";
import { useAuthStore } from "@/shared/api";
import { useChatState } from "@/chat/state";
import { completeOnboarding } from "@/shared/onboarding";

const CopilotSurface = lazy(() =>
  import("./_chat/CopilotSurface").then((m) => ({ default: m.CopilotSurface })),
);

const ONBOARDING_INSTRUCTIONS = `Estás entrevistando al usuario por primera vez para construir su Universo Profesional.
Tu meta: en menos de 5 minutos tener experiencias, educación, skills clave y preferencias básicas.

Plan:
1. Ofrécele al inicio 3 caminos: conectar GitHub (usa la herramienta propose_github_sync), subir su CV en PDF (puede arrastrarlo directamente al chat y lo procesas con propose_pdf_import, o usar los accesos de arriba para LinkedIn/GitHub), o entrevista manual.
2. Si elige la entrevista, pregunta UNA cosa a la vez. Empieza por: "¿En qué trabajas ahora?" → propón una experiencia con propose_entity (el tipo de entidad correspondiente: experience).
3. Después de cada respuesta, usa propose_entity con el tipo adecuado (experience, education, skill, …) en modo HITL. NUNCA escribas directamente en el universo — SIEMPRE vía las herramientas propose_*.
4. Tras 3-4 entries básicas, pregunta por las skills clave y propónlas en bloque con propose_skill_batch.
5. Al final, redirige a /universe.

Tono: cercano, sin jerga, en español por defecto.`;

const INITIAL = `¡Empezamos! En menos de 5 minutos tendrás tu universo profesional montado. ¿Prefieres conectar GitHub o LinkedIn ahora, o que te entreviste para añadir experiencias a mano?`;

interface Shortcut {
  /** Seeds this prompt into the on-page chat (agent drives the import) — the
   *  tiles no longer navigate away from the conversation. */
  prompt: string;
  icon: React.ReactNode;
  badgeTone: "leaf" | "sunbeam" | "stone";
  iconBg: string;
  iconColor: string;
  title: string;
  body: string;
}

const SHORTCUTS: Shortcut[] = [
  {
    prompt: "Quiero importar mi perfil de LinkedIn.",
    icon: <span aria-hidden className="font-bold text-sm">in</span>,
    badgeTone: "leaf",
    iconBg: "bg-[#0a66c2]",
    iconColor: "text-white",
    title: "Importar LinkedIn",
    body: "Sincroniza tu perfil completo en segundos.",
  },
  {
    prompt: "Conecta mi GitHub para traer repos, lenguajes y temas.",
    icon: <GitHubIcon size={20} />,
    badgeTone: "stone",
    iconBg: "bg-ink",
    iconColor: "text-canvas",
    title: "Conectar GitHub",
    body: "Repos, lenguajes y temas como evidencia.",
  },
  {
    prompt: "Quiero subir mi CV en PDF para importarlo.",
    icon: <FileText size={20} />,
    badgeTone: "sunbeam",
    iconBg: "bg-sunbeam",
    iconColor: "text-sunbeam-ink",
    title: "Subir CV (PDF)",
    body: "Parseamos secciones; tú confirmas cada una.",
  },
];

export function OnboardingChatPage() {
  const ready = useCopilotReady();
  const userId = useAuthStore((s) => s.userId);

  // Warm up CopilotKit only when this surface actually mounts (mirrors
  // HomePage/UniversePage), avoiding a module-eval race with the provider.
  useEffect(() => {
    enableCopilot();
  }, []);

  // Reaching onboarding counts as "seen" so the router gate stops funnelling
  // the user back here once they head into the app with an empty universe.
  useEffect(() => {
    completeOnboarding(userId);
  }, [userId]);

  return (
    <div className="bg-canvas pb-24 md:pb-12">
      <Surface width="lg" spacing="md">
        <PageHeader
          eyebrow="Onboarding"
          title="Vamos a montar tu universo"
          subtitle="Conecta tus cuentas o cuéntame de ti. Cada propuesta la confirmas tú con un toque."
        />

        <Stagger className="grid sm:grid-cols-3 gap-3 md:gap-4" delayStep={0.06} initialDelay={0.1}>
          {SHORTCUTS.map((s) => (
            <button
              key={s.title}
              type="button"
              onClick={() => useChatState.getState().setPendingInjection({ content: s.prompt })}
              className="block group w-full text-left"
            >
              <Card padding="md" interactive className="h-full flex flex-col gap-3">
                <span
                  aria-hidden
                  className={`inline-flex w-10 h-10 items-center justify-center rounded-full ${s.iconBg} ${s.iconColor}`}
                >
                  {s.icon}
                </span>
                <div className="space-y-0.5">
                  <h3 className="font-medium text-ink leading-tight">{s.title}</h3>
                  <p className="text-xs text-stone leading-relaxed">{s.body}</p>
                </div>
                <span className="text-xs text-stone group-hover:text-ink mt-auto inline-flex items-center gap-1 transition-colors">
                  Empezar en el chat <ArrowRight size={12} />
                </span>
              </Card>
            </button>
          ))}
        </Stagger>

        <Reveal delay={0.3}>
          <div className="flex items-center gap-3 my-2 text-stone">
            <div className="flex-1 h-px bg-ink/8" />
            <span className="text-xs uppercase tracking-wider">o cuéntame en el chat</span>
            <div className="flex-1 h-px bg-ink/8" />
          </div>
        </Reveal>

        <Reveal delay={0.36}>
          <Card tone="surface" padding="none" className="overflow-hidden">
            <div className="px-5 py-3 border-b border-ink/5 flex items-center gap-2.5">
              <span
                aria-hidden
                className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-leaf-soft text-leaf-ink"
              >
                <Sparkles size={14} />
              </span>
              <div className="text-sm font-medium text-ink">Tu asistente</div>
            </div>
            <div className="h-[440px] min-h-[280px] bg-canvas">
              {ready ? (
                <Suspense fallback={<ChatSkeleton />}>
                  <CopilotSurface
                    instructions={ONBOARDING_INSTRUCTIONS}
                    title="Tu asistente"
                    initial={INITIAL}
                  />
                </Suspense>
              ) : (
                <ChatSkeleton />
              )}
            </div>
          </Card>
        </Reveal>

        <div className="flex flex-wrap gap-2 justify-end pt-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => (window.location.hash = "#/universe")}
            trailingIcon={<ArrowRight size={14} />}
          >
            Saltar al Universo
          </Button>
        </div>
      </Surface>
    </div>
  );
}

function ChatSkeleton() {
  return (
    <div className="flex flex-col h-full p-4 gap-3">
      <div className="flex-1 flex flex-col gap-3 overflow-hidden">
        <Skeleton shape="block" className="h-12 max-w-[60%]" />
        <Skeleton shape="block" className="h-16 max-w-[75%] ml-auto" />
      </div>
      <Skeleton shape="block" className="h-10" />
    </div>
  );
}
