/**
 * Isolated module that imports every CopilotKit-touching surface.
 * Pulled in only when a chat page renders so the heavy chat bundle stays out of
 * the initial app shell.
 *
 * Aligned to CopilotKit 1.57: attachments use the library's NATIVE `attachments`
 * pipeline (no custom drop-target/paperclip — that fought the composer and the
 * floating panel's focus handlers), and failures render in-thread via
 * `ErrorMessage`.
 *
 * NOTE: scroll-back rehydration was removed — seeding `setMessages` with a plain
 * `{id,role,content}` shape corrupts CopilotKit 1.57's message list (user bubbles
 * stop rendering). Restoring history needs proper AG-UI Message construction; the
 * agno backend still keeps session memory so the agent stays context-aware.
 */
import { useEffect } from "react";
import { CopilotChat } from "@copilotkit/react-ui";
import { useCopilotChat, useCoAgentStateRender } from "@copilotkit/react-core";
import { toast } from "@/ui";
import { AgentMessage, PersonMessage, Composer, ErrorMessage } from "@/chat/ChatUI";
import { UniverseActions } from "@/chat/actions";
import { UniverseReadable } from "@/chat/readables";
import { SyncTaskTray } from "@/chat/SyncTaskTray";
import { RemindersBanner } from "@/chat/RemindersBanner";
import { appendUserMessage } from "@/chat/appendMessage";
import { ThinkingSteps } from "@/chat/ThinkingSteps";

interface Props {
  instructions: string;
  title: string;
  initial: string;
}

const ATTACH_ACCEPT = "image/jpeg,image/png,image/webp,image/gif,application/pdf";
const ATTACH_MAX_BYTES = 10 * 1024 * 1024;

export function CopilotSurface({ instructions, title, initial }: Props) {
  // Real-time agent state rendering ( predictive state updates from the backend ).
  // Falls back to heuristic steps in AgentMessage when the backend does not emit
  // explicit agent-state messages.
  useCoAgentStateRender({
    name: "universe_coordinator",
    render: ({ status, state, nodeName }) => {
      const steps = [] as Array<{ id: string; label: string; status: "pending" | "active" | "done" }>;
      const s = state as Record<string, unknown> | undefined;
      if (s?.step) {
        steps.push({ id: "agent-step", label: String(s.step), status: status === "inProgress" ? "active" : "done" });
      } else if (nodeName) {
        const labelMap: Record<string, string> = {
          analyze: "Analizando tu perfil…",
          search: "Buscando experiencias relevantes…",
          score: "Calculando match score…",
          review: "Revisando recordatorios…",
          sync: "Sincronizando datos…",
          draft: "Redactando respuesta…",
        };
        steps.push({ id: nodeName, label: labelMap[nodeName] || nodeName, status: status === "inProgress" ? "active" : "done" });
      }
      if (steps.length === 0) return null;
      return <ThinkingSteps steps={steps} />;
    },
  });

  return (
    <>
      <UniverseActions />
      <UniverseReadable />
      <ChatInjector />
      <InlineEditListener />
      <RemindersBannerLauncher />
      <CopilotChat
        instructions={instructions}
        labels={{ title, initial, placeholder: "Escribe a tu agente…" }}
        AssistantMessage={AgentMessage}
        UserMessage={PersonMessage}
        ErrorMessage={ErrorMessage}
        Input={Composer}
        attachments={{
          enabled: true,
          accept: ATTACH_ACCEPT,
          maxSize: ATTACH_MAX_BYTES,
          // No onUpload → CopilotKit inlines the file as a base64 data part in
          // the next user message; the backend AG-UI run extracts image/PDF
          // parts and feeds them to the model.
          onUploadFailed: (err) =>
            toast.error("Archivo no aceptado", err?.message || "Inténtalo con otro archivo."),
        }}
      />
      <SyncTaskTray />
    </>
  );
}

/** Listens for inline-edit events from AgentMessage and injects them as
 *  a user correction into the active chat thread. */
function InlineEditListener() {
  const chat = useCopilotChat();
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as { original: string; corrected: string } | undefined;
      if (!detail) return;
      appendUserMessage(
        chat,
        `Corrección: en lugar de "${detail.original}" debería ser "${detail.corrected}".`,
      );
    };
    window.addEventListener("cvs-chat-inline-edit", handler);
    return () => window.removeEventListener("cvs-chat-inline-edit", handler);
  }, [chat]);
  return null;
}

/** Thin wrapper that hooks into useCopilotChat so the banner can inject a
 *  prompt when the user clicks "Revisar en el chat". Kept separate from
 *  `RemindersBanner` itself so the banner stays decoupled from CopilotKit. */
function RemindersBannerLauncher() {
  const chat = useCopilotChat();
  return (
    <RemindersBanner
      onAsk={() => {
        appendUserMessage(
          chat,
          "Muéstrame mis recordatorios pendientes con `preview_list` y dime cuáles debería atender primero.",
        );
      }}
    />
  );
}

/**
 * Consumes one-shot prompts dropped via sessionStorage (e.g. "Edit this CV
 * section"). Appends them as a user message into the active chat thread.
 */
function ChatInjector() {
  const chat = useCopilotChat();
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("cvs-saas-chat-inject");
      if (!raw) return;
      sessionStorage.removeItem("cvs-saas-chat-inject");
      const data = JSON.parse(raw) as { content: string };
      if (!data.content) return;
      // Minor delay so CopilotChat finishes mounting before we push.
      setTimeout(() => {
        appendUserMessage(chat, data.content);
      }, 300);
    } catch {
      /* ignore */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return null;
}
