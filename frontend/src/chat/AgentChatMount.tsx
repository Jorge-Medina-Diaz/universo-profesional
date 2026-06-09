/**
 * AgentChatMount — the ONE place the agent chat surface is mounted.
 *
 * Previously the FloatingChat + CopilotSurface pair was duplicated in three
 * places (HomePage, UniversePage, GlobalAgentDock) that differed only by three
 * strings (instructions / title / initial). They are now derived from the route
 * via {@link chatFraming}. The backend pins thread_id = main-<user_id>, so the
 * conversation already follows the user across surfaces; only the opening
 * framing + page hint change.
 *
 * Exactly one AgentChatMount is mounted at rest: the home/universe surfaces
 * render it directly, and GlobalAgentDock renders it on every other page
 * (suppressing itself on the routes that own one — see GlobalAgentDock).
 */
import { Suspense, lazy, useEffect } from "react";
import { useHashRoute } from "@/shared/useHashRoute";
import { enableCopilot, useCopilotReady } from "@/app/CopilotProvider";
import { FloatingChat } from "@/chat/FloatingChat";
import { ChatLoadingSkeleton } from "@/chat/ChatLoadingSkeleton";

const CopilotSurface = lazy(() =>
  import("@/pages/_chat/CopilotSurface").then((m) => ({ default: m.CopilotSurface })),
);

const HOME_INSTRUCTIONS = `Eres el compañero agéntico del usuario.
Habla en español por defecto y en inglés si el usuario te lo pide.
Tu trabajo es ENTENDER, ESTRUCTURAR y MANTENER su universo profesional a lo largo del tiempo.

REGLAS:
1. Coherencia primero. Antes de proponer algo nuevo, considera si es una actualización de algo existente.
   El motor de upsert decidirá merge vs new — tú solo pasa los datos.
2. Una pregunta por turno. Si te describe varias cosas, despiézalas y rutea al specialist correspondiente.
3. Captura narrativa libre (opiniones, lo que está aprendiendo, gustos) en notes; datos estructurados
   en universe entities; documentos largos en knowledge.
4. NUNCA guardes sin confirmación: usa las propose_* tools que muestran cards en el chat.
5. Cuando detectes que pasó tiempo, pregunta proactivamente por evolución (¿sigues en X?, ¿completaste Y?).
6. Si el usuario menciona varias skills relacionadas en un solo turno (un stack, "trabajo con X/Y/Z"),
   usa propose_skill_batch en lugar de varias propose_skill — el usuario las confirma de golpe.
7. Cuando el usuario pegue una oferta o URL de empleo, llama a la tool MCP match_job_to_profile
   y después invoca present_job_match con el resultado para mostrar la scorecard visual.
8. Cuando el usuario quiera VER / EXPLORAR su universo, usa \`universe_retrieve\` para encontrar los
   nodos y luego \`present_graph_view(mode)\` para mostrar el grafo navegable. Para vistas analíticas
   derivadas usa \`present_widget\` (tech_radar, job_match, goals_progress, learning_trajectory, …).`;

const HOME_INITIAL = `Hola. Soy tu compañero para construir y mantener tu universo profesional. ¿Por dónde quieres empezar?`;

const UNIVERSE_INSTRUCTIONS = `Eres el compañero agéntico del usuario, sobre su universo profesional en formato grafo navegable.
Habla en español por defecto. Tu trabajo es ayudarle a EXPLORAR y MANTENER su universo.
- PILOTA EL GRAFO, no lo describas. Cuando el usuario quiera ver/explorar algo, primero lee el readable \`graph_view\` (modo actual, filtros, nodos visibles con sus ids) y luego MANIPULA la constelación:
  • \`control_graph\` para filtrar (filter_kinds), ocultar áreas (hide_areas), cambiar lente (color_by 'area'|'pillar'), buscar (search), enfocar un nodo (focus_entity_id, usa ids reales del readable) o activar grafo local (local_depth 1-3).
  • \`animate_graph\` para llevar la vista: 'flyTo' (vuelo de cámara a un nodo), 'pulse'/'highlightSet' (ilumina un conjunto de nodos — p.ej. las skills que pide un rol), 'reset'.
  • \`present_graph_view(mode, focus_entity_id?)\` para cambiar de lente (focus | cluster | timeline | outline).
  Ej.: "enséñame mi stack de datos y haz zoom" → control_graph(filter_kinds=['skill','project']) y animate_graph(type='flyTo', entity_id=<ancla>).
- MUESTRA con cards generativas en vez de párrafos: \`present_trajectory\` (línea de tiempo de su carrera), \`present_experience_card\`, \`present_project_card\`, \`present_skill_gap\` (encaje para un rol con ring + chips). Pasa los entity_id/entity_ids para que la card pueda iluminar esos nodos en el grafo.
- Coherencia primero: antes de crear algo nuevo, considera si es una actualización. Usa las propose_* tools (muestran cards) y nunca guardes sin confirmación.
- Una pregunta por turno.`;

const UNIVERSE_INITIAL = `Este es tu universo. Pídeme que te enseñe un área ("muéstrame mi stack de backend"), que enfoque algo, o cuéntame algo nuevo para añadirlo.`;

const BASE_INSTRUCTIONS = `Eres el agente del Universo Profesional del usuario: su copiloto para construir y mantener su carrera. Trabajas en modo conversacional — el usuario te pide algo y TÚ haces el trabajo, proponiendo cambios que él confirma (HITL). Tienes herramientas para crear y editar experiencias, educación, skills, metas, ofertas de empleo, documentos (CV y cartas), recordatorios, y para importar de GitHub/LinkedIn/PDF. NUNCA escribas directo en el universo: usa SIEMPRE las herramientas propose_* (cambios) y present_* (vistas). Responde en español por defecto, cercano y sin jerga.`;

const BASE_INITIAL = `¿En qué te ayudo? Puedo trabajar en tu universo, generar documentos, gestionar tus ofertas y más — tú confirmas cada cambio.`;

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

/**
 * Low-typing / proactive doctrine appended to EVERY framing. This is the lever
 * that turns the assistant from "asks long text questions" into "emits tappable
 * widgets the user confirms" — the difference between a chatbot that interrogates
 * and an assistant that proposes.
 */
const LOW_TYPING_DOCTRINE = `

PROPÓN, NO PREGUNTES (experiencia fluida, mínimo tecleo):
- Cuando necesites datos, NO los pidas en prosa: emite un widget TOCABLE.
  • Varias preguntas relacionadas → \`present_questionnaire\` (mezcla single_choice / multi_choice / scale; incluye \`options\` para que el usuario las toque, deja \`open\` solo para texto genuinamente libre).
  • Explorar un tema/dominio → \`present_deep_dive\` (secciones con chips/escala).
  • Un stack o varias skills → \`propose_skill_batch\`.
  • Una entidad concreta → la \`propose_*\` correspondiente, RELLENA con valores por defecto razonables para que el usuario solo confirme/ajuste.
- Máximo UNA pregunta de texto libre por turno, y solo si ninguna opción tocable sirve.
- Lidera con lo que ya sabes ("Doy casi todo por hecho, confírmame solo estas 3 cosas") en vez de interrogar campo a campo.
- Ofrece siempre opciones concretas para tocar antes que pedir que el usuario escriba.

MUESTRA, NO SÓLO CUENTES (UI generativa):
- Cuando hables de la carrera, experiencias, proyectos o encaje con un rol, RENDERIZA una card en vez de un párrafo largo: \`present_trajectory\` (línea de tiempo), \`present_experience_card\`, \`present_project_card\`, \`present_skill_gap\`. Reúne datos con una read tool primero y pasa los entity_id para enlazar la card con el grafo.
- En /universe puedes además PILOTAR la constelación con \`control_graph\` (filtrar/ocultar/enfocar/lente) y \`animate_graph\` (vuelo de cámara, iluminar nodos). Prefiere enseñar sobre el grafo antes que enumerar en texto.`;

export interface ChatFraming {
  instructions: string;
  title: string;
  initial: string;
}

/** Resolve the chat's opening framing from the current route. */
export function chatFraming(path: string): ChatFraming {
  if (path === "/")
    return { instructions: HOME_INSTRUCTIONS + LOW_TYPING_DOCTRINE, title: "Universo profesional", initial: HOME_INITIAL };
  if (path.startsWith("/universe"))
    return { instructions: UNIVERSE_INSTRUCTIONS + LOW_TYPING_DOCTRINE, title: "Tu universo · chat", initial: UNIVERSE_INITIAL };
  return {
    instructions: BASE_INSTRUCTIONS + routeHint(path) + LOW_TYPING_DOCTRINE,
    title: "Tu agente",
    initial: BASE_INITIAL,
  };
}

export interface AgentChatMountProps {
  onExpandedChange?: (expanded: boolean) => void;
}

export function AgentChatMount({ onExpandedChange }: AgentChatMountProps) {
  const path = useHashRoute();
  const ready = useCopilotReady();
  const framing = chatFraming(path);

  // Warm up CopilotKit when the chat surface mounts (idempotent).
  useEffect(() => {
    enableCopilot();
  }, []);

  return (
    <FloatingChat onExpandedChange={onExpandedChange}>
      {ready ? (
        <Suspense fallback={<ChatLoadingSkeleton />}>
          <CopilotSurface
            instructions={framing.instructions}
            title={framing.title}
            initial={framing.initial}
          />
        </Suspense>
      ) : (
        <ChatLoadingSkeleton />
      )}
    </FloatingChat>
  );
}
