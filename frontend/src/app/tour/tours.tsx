import { openCommandPalette } from "@/app/CommandPalette";
import type { TourDefinition } from "./TourProvider";

/** First-run tour shown the first time an authed user lands on Home. */
export const firstRunTour: TourDefinition = {
  id: "first-run-v1",
  steps: [
    {
      id: "welcome",
      placement: "center",
      title: "Bienvenido a tu Universo Profesional",
      body: (
        <>
          Te enseño los cuatro sitios clave en menos de 30 segundos. Puedes
          saltarlo con <kbd className="text-[10px] bg-surface px-1.5 py-0.5 rounded">Esc</kbd>{" "}
          en cualquier momento.
        </>
      ),
    },
    {
      id: "chat",
      target: "home-chat-header",
      placement: "bottom",
      title: "El chat es tu interfaz principal",
      body: "Cuéntale lo que haces y propondrá entradas en tu universo. Cada propuesta la confirmas con un toque.",
    },
    {
      id: "drawer",
      target: "open-universe-button",
      placement: "left",
      title: "Tu universo, siempre a un clic",
      body: "Abre este panel para ver tu trayectoria, sugerencias y conexiones — sin salir del chat.",
    },
    {
      id: "command",
      target: "command-palette-trigger",
      placement: "bottom",
      title: "⌘K para saltar a cualquier sitio",
      body: "Busca cualquier sección al instante. Ahorra clicks cuando ya conoces el producto.",
      cta: {
        label: "Probarlo",
        onClick: () => openCommandPalette(),
      },
    },
    {
      id: "reminders",
      target: "reminders-bell",
      placement: "bottom",
      title: "Te avisamos cuando algo necesita tu atención",
      body: "Certificaciones que expiran, cursos en pausa, sugerencias acumuladas… todo aquí.",
    },
    {
      id: "finish",
      placement: "center",
      title: "Listo, ahora a construir",
      body: (
        <>
          Si quieres, importa primero LinkedIn / GitHub / un PDF en{" "}
          <a href="#/connections" className="text-ink underline-offset-2 hover:underline">
            Conexiones
          </a>
          . O empieza a hablar y deja que el agente te guíe.
        </>
      ),
    },
  ],
};
