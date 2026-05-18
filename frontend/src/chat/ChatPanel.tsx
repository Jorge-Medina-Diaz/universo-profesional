/**
 * Adaptive chat surface:
 *  - Desktop ≥ 768px → CopilotSidebar (right-side)
 *  - Mobile  < 768px → floating button → Vaul bottom-sheet with CopilotChat
 */
import { CopilotChat, CopilotSidebar } from "@copilotkit/react-ui";
import { useEffect, useState } from "react";
import { Drawer } from "vaul";
import { UniverseActions } from "./actions";
import { UniverseReadable } from "./readables";

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    setIsMobile(mq.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return isMobile;
}

const SYSTEM_INSTRUCTIONS = `Eres el asistente del Universo Profesional del usuario.
Habla en español por defecto y en inglés si el usuario te lo pide.
Tu trabajo es:
 1. AYUDAR al usuario a construir y mantener su universo profesional (educations, experiences, projects, skills, certifications, languages, achievements, intereses, career preferences).
 2. Cuando detectes información que merece añadirse, USA las acciones propose* (proposeExperienceEntry, proposeEducationEntry, proposeProjectEntry, proposeSkillEntry). NUNCA escribas sin la confirmación del usuario — todas son HITL.
 3. Para importar GitHub, llama proposeGithubSync. Para LinkedIn / PDF guía al usuario a /connections.
 4. Si hay suggestion ids en el contexto, ofrece applySuggestion con accept/reject.
 5. Mantén respuestas breves. Una pregunta cada vez. Si el usuario te describe algo largo, despiézalo en cards confirmables.`;

const INITIAL_MESSAGE = `¡Hola! Soy tu asistente para tu universo profesional. ¿Quieres conectar GitHub o LinkedIn ahora, o prefieres que te entreviste para añadir experiencias a mano?`;

export function ChatPanel() {
  const isMobile = useIsMobile();
  if (isMobile) return <MobileChat />;
  return (
    <>
      <UniverseActions />
      <UniverseReadable />
      <CopilotSidebar
        instructions={SYSTEM_INSTRUCTIONS}
        labels={{ title: "Tu asistente", initial: INITIAL_MESSAGE }}
        defaultOpen={false}
        clickOutsideToClose
      />
    </>
  );
}

function MobileChat() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <UniverseActions />
      <UniverseReadable />
      <button
        aria-label="Abrir chat"
        onClick={() => setOpen(true)}
        className="fixed bottom-20 right-4 z-30 h-14 w-14 rounded-full bg-brand-600 text-white shadow-lg flex items-center justify-center"
      >
        💬
      </button>
      <Drawer.Root open={open} onOpenChange={setOpen}>
        <Drawer.Portal>
          <Drawer.Overlay className="fixed inset-0 bg-black/40 z-40" />
          <Drawer.Content className="bg-white flex flex-col fixed bottom-0 left-0 right-0 max-h-[90vh] rounded-t-2xl z-50">
            <div className="mx-auto my-2 h-1 w-12 rounded bg-gray-300" />
            <Drawer.Title className="sr-only">Asistente</Drawer.Title>
            <div className="flex-1 min-h-0 px-2 pb-2">
              <CopilotChat
                instructions={SYSTEM_INSTRUCTIONS}
                labels={{ title: "Tu asistente", initial: INITIAL_MESSAGE }}
              />
            </div>
          </Drawer.Content>
        </Drawer.Portal>
      </Drawer.Root>
    </>
  );
}
