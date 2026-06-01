/**
 * GlobalAgentDock — the agent, everywhere.
 *
 * Mounted ONCE in the authenticated Layout so EVERY page has a persistent,
 * collapsible chat dock. The product is chat-first ("toda la experiencia del
 * usuario debe ser agéntica"): previously the agent reached only 3 of 13
 * authenticated pages. The dock reuses the same FloatingChat + CopilotSurface
 * as the home constellation, so streaming + HITL cards behave identically, and
 * the backend pins thread_id = main-<user_id> so the conversation follows the
 * user across every surface (and across the dock ↔ page-chat swap).
 *
 * It steps aside on routes that already mount their OWN CopilotSurface (home,
 * universe, onboarding) so we never mount two CopilotChat instances at rest —
 * which would double-register the propose_ and present_ actions.
 */
import { Suspense, lazy, useEffect } from "react";
import { useHashRoute } from "@/shared/useHashRoute";
import { enableCopilot, useCopilotReady } from "@/app/CopilotProvider";
import { FloatingChat } from "@/chat/FloatingChat";
import { Skeleton } from "@/ui";

const CopilotSurface = lazy(() =>
  import("@/pages/_chat/CopilotSurface").then((m) => ({
    default: m.CopilotSurface,
  })),
);

/** Routes whose page mounts its own CopilotSurface — the dock steps aside so
 *  exactly one CopilotChat is mounted at rest. */
function ownsChat(path: string): boolean {
  return (
    path === "/" || path.startsWith("/universe") || path === "/onboarding/chat"
  );
}

const BASE_INSTRUCTIONS = `Eres el agente del Universo Profesional del usuario: su copiloto para construir y mantener su carrera. Trabajas en modo conversacional — el usuario te pide algo y TÚ haces el trabajo, proponiendo cambios que él confirma (HITL). Tienes herramientas para crear y editar experiencias, educación, skills, metas, ofertas de empleo, documentos (CV y cartas), recordatorios, y para importar de GitHub/LinkedIn/PDF. NUNCA escribas directo en el universo: usa SIEMPRE las herramientas propose_* (cambios) y present_* (vistas). Responde en español por defecto, cercano y sin jerga.`;

/** Page-aware focus appended to the base instructions so the agent leads with
 *  the most relevant action for wherever the user currently is. */
function routeHint(path: string): string {
  if (path.startsWith("/jobs"))
    return " El usuario está en sus ofertas de empleo: puedes añadir una oferta (propose_job_create), cambiar su estado (propose_job_status_change), lanzar el autopilot (propose_autopilot_run) o mostrar el match (present_job_match).";
  if (path.startsWith("/cv") || path.startsWith("/documents"))
    return " El usuario está en sus documentos: puedes generar un CV (propose_document_generation), una carta de presentación (propose_cover_letter) o regenerar (propose_cv_regenerate), y mostrar el resultado con present_document_preview.";
  if (path.startsWith("/notes"))
    return " El usuario está en sus notas: ayúdale a capturar y estructurar ideas, conectándolas con entidades de su universo.";
  if (path.startsWith("/reminders"))
    return " El usuario está en sus recordatorios: ayúdale a revisarlos y priorizar cuáles atender primero (preview_list).";
  if (path.startsWith("/preferences"))
    return " El usuario está en sus preferencias de carrera: ayúdale a definir qué busca (rol, salario, modalidad remota…) con propose_preferences_update.";
  if (path.startsWith("/connections"))
    return " El usuario está en conexiones: ofrécele importar de GitHub (propose_github_sync), LinkedIn, o subir su CV en PDF (propose_pdf_import).";
  if (
    path.startsWith("/settings") ||
    path.startsWith("/billing") ||
    path.startsWith("/usage") ||
    path.startsWith("/mcp")
  )
    return " El usuario está en ajustes/cuenta: resuelve sus dudas y, si procede, guíale a la acción adecuada.";
  return "";
}

const INITIAL = `¿En qué te ayudo? Puedo trabajar en tu universo, generar documentos, gestionar tus ofertas y más — tú confirmas cada cambio.`;

export function GlobalAgentDock() {
  const path = useHashRoute();
  const ready = useCopilotReady();
  const suppressed = ownsChat(path);

  // Warm up CopilotKit when a dock-bearing page is showing (idempotent).
  useEffect(() => {
    if (!suppressed) enableCopilot();
  }, [suppressed]);

  if (suppressed) return null;

  return (
    <FloatingChat>
      {ready ? (
        <Suspense fallback={<DockSkeleton />}>
          <CopilotSurface
            instructions={BASE_INSTRUCTIONS + routeHint(path)}
            title="Tu agente"
            initial={INITIAL}
          />
        </Suspense>
      ) : (
        <DockSkeleton />
      )}
    </FloatingChat>
  );
}

function DockSkeleton() {
  return (
    <div className="flex flex-col h-full p-4 gap-3">
      <div className="flex-1 flex flex-col gap-3 overflow-hidden">
        <Skeleton shape="block" className="h-10 max-w-[55%]" />
        <Skeleton shape="block" className="h-14 max-w-[72%] ml-auto" />
      </div>
      <Skeleton shape="block" className="h-10" />
    </div>
  );
}
