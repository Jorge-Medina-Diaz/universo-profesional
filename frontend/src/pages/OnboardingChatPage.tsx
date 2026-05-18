/**
 * Conversational onboarding — replaces the rigid 7-step wizard.
 *
 * The CopilotKit chat is the primary surface; we render a contextual
 * "shortcuts" panel next to it with the high-leverage actions (Connect GitHub,
 * Upload LinkedIn ZIP, Upload PDF, Skip to manual).
 */
import { CopilotChat } from "@copilotkit/react-ui";
import { UniverseActions } from "@/chat/actions";
import { UniverseReadable } from "@/chat/readables";

const ONBOARDING_INSTRUCTIONS = `Estás entrevistando al usuario por primera vez para construir su Universo Profesional.
Tu meta: en menos de 5 minutos tener experiencias, educación, skills clave y preferencias básicas.

Plan:
1. Ofrécele al inicio 3 caminos: conectar GitHub (proposeGithubSync), subir LinkedIn/CV (dirígele a /connections), o entrevista manual.
2. Si elige la entrevista, pregunta UNA cosa a la vez. Empezar por: "¿En qué trabajas ahora?" → propón una experience card.
3. Después de cada respuesta del usuario, usa la propose*Entry adecuada (HITL). NUNCA llames add_* directamente — siempre via propose*.
4. Tras 3-4 entries básicas, pregunta por skills clave y propón proposeSkillEntry.
5. Al final, redirige a /universe.

Tono: cercano, sin jerga, en español por defecto.`;

const INITIAL = `¡Empezamos! En menos de 5 minutos tendrás tu universo profesional montado. ¿Prefieres conectar GitHub o LinkedIn ahora, o que te entreviste para añadir experiencias a mano?`;

export function OnboardingChatPage() {
  return (
    <div className="max-w-3xl mx-auto py-4 px-4 pb-24 md:pb-6 h-[calc(100vh-3.5rem)] flex flex-col">
      <UniverseActions />
      <UniverseReadable />
      <header className="mb-3">
        <h1 className="text-xl font-bold">Vamos a montar tu universo</h1>
        <p className="text-xs text-gray-600">
          Conecta tus cuentas o cuéntame de ti. Cada propuesta la confirmas tú con un tap.
        </p>
      </header>
      <div className="flex-1 min-h-0 border border-gray-200 rounded-lg overflow-hidden">
        <CopilotChat
          instructions={ONBOARDING_INSTRUCTIONS}
          labels={{ title: "Tu asistente", initial: INITIAL }}
        />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <a href="#/connections" className="btn-secondary text-xs">
          🔗 Ir a Conexiones
        </a>
        <a href="#/universe" className="btn-secondary text-xs">
          🪐 Saltar al Universo
        </a>
      </div>
    </div>
  );
}
