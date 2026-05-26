interface ChatApi {
  appendMessage?: (message: { role: "user"; content: string }) => void;
}

/**
 * Type-safe helper to append a user message to a CopilotKit chat.
 * Isolates the `unknown` casting that CopilotSurface previously did inline.
 */
export function appendUserMessage(chat: unknown, content: string): void {
  const api = chat as ChatApi;
  if (typeof api.appendMessage !== "function") return;
  try {
    api.appendMessage({ role: "user", content });
  } catch {
    /* ignore — API moved between versions */
  }
}
