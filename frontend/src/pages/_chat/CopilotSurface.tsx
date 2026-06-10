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
 * Scroll-back rehydration is BACK (P2.B): useChatRehydration seeds the thread
 * with proper `TextMessage` instances (the documented-safe construction — the
 * old plain `{id,role,content}` literals corrupted CopilotKit 1.57's list).
 */
import { useEffect } from "react";
import { CopilotChat } from "@copilotkit/react-ui";
// Inline the CopilotKit CSS as a string so Vite does NOT extract it into a
// separate stylesheet that gets hoisted into index.html. The styles are only
// injected when this lazy chunk actually loads (~29 KB, gzipped ~6 KB).
import copilotkitCss from "@copilotkit/react-ui/styles.css?inline";
import { useCopilotChat, useCoAgent, useCoAgentStateRender } from "@copilotkit/react-core";
import { toast } from "@/ui";
import { AgentMessage, PersonMessage, Composer, ErrorMessage } from "@/chat/ChatUI";
import { UniverseActions } from "@/chat/actions";
import { UniverseReadable } from "@/chat/readables";
import { SyncTaskTray } from "@/chat/SyncTaskTray";
import { RemindersBanner } from "@/chat/RemindersBanner";
import { appendUserMessage } from "@/chat/appendMessage";
import { ThinkingSteps } from "@/chat/ThinkingSteps";
import { useChatState } from "@/chat/state";
import {
  AGENT_NAME,
  agentStatusLabel,
  thinkingStepsFromState,
  type AgentSharedState,
} from "@/chat/agentState";
import { useChatRehydration } from "@/chat/useChatRehydration";

interface Props {
  instructions: string;
  title: string;
  initial: string;
}

const ATTACH_ACCEPT = "image/jpeg,image/png,image/webp,image/gif,application/pdf";
const ATTACH_MAX_BYTES = 10 * 1024 * 1024;

export function CopilotSurface({ instructions, title, initial }: Props) {
  // Inject CopilotKit styles dynamically so they stay out of the entry HTML.
  useEffect(() => {
    const style = document.createElement("style");
    style.textContent = copilotkitCss;
    document.head.appendChild(style);
    return () => {
      document.head.removeChild(style);
    };
  }, []);

  // P2.B — REAL shared state from the backend (STATE_SNAPSHOT + STATE_DELTAs,
  // see backend state_emitter.py). Replaces the old nodeName heuristics.
  const { state: agentState } = useCoAgent<AgentSharedState>({ name: AGENT_NAME });

  // The chat's actual run lifecycle. If a run dies (RUN_ERROR / network drop)
  // no final state delta ever arrives, so the shared state alone would leave
  // the dock chip stuck on "Pensando…" forever.
  const { isLoading } = useCopilotChat();

  // Publish the humanized status into the Zustand store so always-mounted
  // chrome (FloatingChat's collapsed-dock chip) can show it WITHOUT importing
  // the heavy CopilotKit bundle. Cleared on unmount so no stale chip lingers.
  const setAgentActivity = useChatState((s) => s.setAgentActivity);
  useEffect(() => {
    if (isLoading) {
      // Normal flow: mirror the streamed shared state while the run is live.
      const label = agentStatusLabel(agentState);
      setAgentActivity(
        label && agentState?.agent_status
          ? { status: agentState.agent_status, label }
          : null,
      );
      return;
    }
    // Run finished (or died without a final delta) → force idle. Small grace
    // so the chip doesn't flicker between "answering" and the message landing.
    const t = setTimeout(() => setAgentActivity(null), 1000);
    return () => clearTimeout(t);
  }, [agentState, isLoading, setAgentActivity]);
  useEffect(() => () => setAgentActivity(null), [setAgentActivity]);

  // Scroll-back rehydration (P2.B) — fills an empty thread from
  // GET /agui/threads/main-{userId}/messages after a reload.
  useChatRehydration();

  // In-thread progress pipeline driven by the same shared state.
  useCoAgentStateRender<AgentSharedState>({
    name: AGENT_NAME,
    render: ({ status, state }) => {
      const steps = thinkingStepsFromState(state, status === "inProgress");
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
 * Consumes one-shot prompts dropped into the Zustand store (e.g. "Edit this CV
 * section"). Appends them as a user message into the active chat thread.
 *
 * Reactive: subscribes to `pendingInjection` so messages are delivered even
 * when CopilotSurface is already mounted.
 */
function ChatInjector() {
  const chat = useCopilotChat();
  const pendingInjection = useChatState((s) => s.pendingInjection);
  const setPendingInjection = useChatState((s) => s.setPendingInjection);

  useEffect(() => {
    if (!pendingInjection?.content) return;
    // Clear immediately so a re-render doesn't re-append.
    setPendingInjection(null);
    // Minor delay so CopilotChat finishes any internal init before we push.
    const t = setTimeout(() => {
      appendUserMessage(chat, pendingInjection.content);
    }, 150);
    return () => clearTimeout(t);
  }, [pendingInjection, chat, setPendingInjection]);

  return null;
}
