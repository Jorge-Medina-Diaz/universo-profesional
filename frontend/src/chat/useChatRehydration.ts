/**
 * useChatRehydration — repopulate the chat with the persisted conversation
 * after a full reload, so the thread is never blank when the backend already
 * remembers it (GET /agui/threads/main-{userId}/messages).
 *
 * WHY THIS IS SAFE NOW (the previous attempt corrupted CopilotKit 1.57):
 * seeding `setMessages` with plain `{id, role, content}` literals broke the
 * message list because the deprecated gql pipeline calls class methods
 * (`isTextMessage()` etc.) on each entry. The documented-safe path is to
 * construct REAL `TextMessage` instances from `@copilotkit/runtime-client-gql`
 * — `useCopilotChatInternal().setMessages` detects `instanceof Message` and
 * converts them through `gqlToAGUI()` into proper AG-UI messages before they
 * reach the agent store (verified in @copilotkit/react-core 1.57.1 dist).
 *
 * Guards:
 *  - runs once per page load (ref; StrictMode-safe — refs survive the
 *    double-effect pass and the seeded store survives surface remounts),
 *  - only when the agent is connected (`isAvailable`) so `agent.setMessages`
 *    targets the live agent AFTER connect replay, never a provisional one,
 *  - never while a run is in progress, never clobbers a non-empty chat
 *    (re-checked after the fetch resolves),
 *  - fetch failures surface via toast (no-silent-errors).
 */
import { useEffect, useRef } from "react";
import { useCopilotChatInternal } from "@copilotkit/react-core";
import { TextMessage, MessageRole } from "@copilotkit/runtime-client-gql";
import { chat, useAuthStore } from "@/shared/api";
import { toast } from "@/ui";

const HISTORY_LIMIT = 60;

export function useChatRehydration(): void {
  const { messages, setMessages, isLoading, isAvailable } = useCopilotChatInternal();
  const startedRef = useRef(false);

  // Latest-value refs so the async fetch re-checks CURRENT chat state before
  // seeding (avoids clobbering a message the user sent while we fetched).
  const liveRef = useRef({ messages, isLoading, setMessages });
  liveRef.current = { messages, isLoading, setMessages };

  const userId = useAuthStore((s) => s.userId);
  const empty = messages.length === 0;

  useEffect(() => {
    if (startedRef.current) return;
    if (!isAvailable || !userId) return;
    if (!empty || isLoading) {
      // The session already has live messages — nothing to rehydrate, and we
      // must never replace an active conversation.
      startedRef.current = true;
      return;
    }
    startedRef.current = true;

    // NOTE: no abort-on-unmount — the seed targets the agent's GLOBAL message
    // store (it survives surface remounts), so completing after a route change
    // is desirable. Under StrictMode the second effect pass exits via
    // startedRef instead of cancelling the in-flight fetch.
    void (async () => {
      try {
        const resp = await chat.threadMessages(`main-${userId}`, HISTORY_LIMIT);
        const history = (resp.messages ?? []).filter(
          (m) =>
            (m.role === "user" || m.role === "assistant") &&
            typeof m.content === "string" &&
            m.content.trim().length > 0,
        );
        if (history.length === 0) return;

        // Re-check against the LIVE chat: a run may have started or a message
        // may have been sent while the fetch was in flight.
        const live = liveRef.current;
        if (live.isLoading || live.messages.length > 0) return;

        live.setMessages(
          history.map(
            (m) =>
              new TextMessage({
                id: m.id,
                role: m.role === "user" ? MessageRole.User : MessageRole.Assistant,
                content: m.content,
                createdAt: m.createdAt ? new Date(m.createdAt) : new Date(),
              }),
          ),
        );
      } catch (err) {
        toast.error(
          "No pude recuperar el historial del chat",
          (err as Error)?.message || "La conversación sigue disponible para el agente.",
        );
      }
    })();
  }, [isAvailable, userId, empty, isLoading]);
}
