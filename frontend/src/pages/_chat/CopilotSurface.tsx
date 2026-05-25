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
import { useCopilotChat } from "@copilotkit/react-core";
import { toast } from "@/ui";
import { AgentMessage, PersonMessage, Composer, ErrorMessage } from "@/chat/ChatUI";
import { UniverseActions } from "@/chat/actions";
import { UniverseReadable } from "@/chat/readables";
import { SyncTaskTray } from "@/chat/SyncTaskTray";
import { RemindersBanner } from "@/chat/RemindersBanner";

interface Props {
  instructions: string;
  title: string;
  initial: string;
}

const ATTACH_ACCEPT = "image/jpeg,image/png,image/webp,image/gif,application/pdf";
const ATTACH_MAX_BYTES = 10 * 1024 * 1024;

export function CopilotSurface({ instructions, title, initial }: Props) {
  return (
    <>
      <UniverseActions />
      <UniverseReadable />
      <ChatInjector />
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

/** Thin wrapper that hooks into useCopilotChat so the banner can inject a
 *  prompt when the user clicks "Revisar en el chat". Kept separate from
 *  `RemindersBanner` itself so the banner stays decoupled from CopilotKit. */
function RemindersBannerLauncher() {
  const chat = useCopilotChat() as unknown as Record<string, unknown>;
  return (
    <RemindersBanner
      onAsk={() => {
        const append = chat.appendMessage as ((m: unknown) => void) | undefined;
        if (typeof append !== "function") return;
        try {
          append({
            role: "user",
            content:
              "Muéstrame mis recordatorios pendientes con `preview_list` y dime cuáles debería atender primero.",
          });
        } catch {
          /* ignore — API moved between versions */
        }
      }}
    />
  );
}

/**
 * Consumes one-shot prompts dropped via sessionStorage (e.g. "Edit this CV
 * section"). Appends them as a user message into the active chat thread.
 */
function ChatInjector() {
  const chat = useCopilotChat() as unknown as Record<string, unknown>;
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("cvs-saas-chat-inject");
      if (!raw) return;
      sessionStorage.removeItem("cvs-saas-chat-inject");
      const data = JSON.parse(raw) as { content: string };
      if (!data.content) return;
      const append = chat.appendMessage as ((m: unknown) => void) | undefined;
      if (typeof append !== "function") return;
      // Minor delay so CopilotChat finishes mounting before we push.
      setTimeout(() => {
        try {
          append({ role: "user", content: data.content });
        } catch {
          /* ignore — API moved between versions */
        }
      }, 300);
    } catch {
      /* ignore */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return null;
}
