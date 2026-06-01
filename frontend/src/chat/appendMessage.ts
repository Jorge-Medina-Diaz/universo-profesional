import { TextMessage, MessageRole } from "@copilotkit/runtime-client-gql";
import { surfaceAgentError } from "@/app/silenceBenignErrors";

interface ChatApi {
  sendMessage?: (message: TextMessage) => Promise<void>;
}

/**
 * Type-safe helper to append a user message to a CopilotKit chat.
 *
 * Uses {@link sendMessage} (not the deprecated {@link appendMessage}) because
 * CopilotKit v1.57's `appendMessage` internally calls `gqlToAGUI` on a plain
 * object, which crashes with `isResultMessage is not a function`.
 * `sendMessage` accepts a proper {@link TextMessage} instance and passes it
 * straight to the agent, bypassing the broken conversion path.
 */
export function appendUserMessage(chat: unknown, content: string): void {
  const api = chat as ChatApi;
  if (typeof api.sendMessage !== "function") return;
  try {
    // Surface async send failures instead of dropping them on the floor
    // (see [[no-silent-errors]]). A version-shape mismatch is handled by the
    // early return above; this catches real send/runtime failures.
    void api
      .sendMessage(new TextMessage({ content, role: MessageRole.User }))
      .catch((err) =>
        surfaceAgentError(
          `No pude enviar tu mensaje al agente: ${(err as Error)?.message ?? ""}`,
        ),
      );
  } catch (err) {
    surfaceAgentError(
      `No pude enviar tu mensaje al agente: ${(err as Error)?.message ?? ""}`,
    );
  }
}
