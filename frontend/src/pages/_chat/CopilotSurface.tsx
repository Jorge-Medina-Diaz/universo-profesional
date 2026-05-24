/**
 * Isolated module that imports every CopilotKit-touching surface.
 * Pulled in only when HomePage renders so the 3 MB chat bundle stays
 * out of the initial app shell.
 */
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type DragEvent,
} from "react";
import { CopilotChat } from "@copilotkit/react-ui";
import { useCopilotChat } from "@copilotkit/react-core";
import { FileUp, Loader2, Paperclip } from "lucide-react";
import { api, useAuthStore } from "@/shared/api";
import { toast } from "@/ui";
import { UniverseActions } from "@/chat/actions";
import { UniverseReadable } from "@/chat/readables";
import { SyncTaskTray } from "@/chat/SyncTaskTray";
import { RemindersBanner } from "@/chat/RemindersBanner";

interface Props {
  instructions: string;
  title: string;
  initial: string;
}

export function CopilotSurface({ instructions, title, initial }: Props) {
  return (
    <>
      <UniverseActions />
      <UniverseReadable />
      <ChatRehydrator />
      <ChatInjector />
      <RemindersBannerLauncher />
      <ChatDropTarget>
        <CopilotChat
          instructions={instructions}
          labels={{ title, initial, placeholder: "Escribe a tu agente…" }}
        />
      </ChatDropTarget>
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
        const append =
          (chat.appendMessage as ((m: unknown) => void) | undefined) ??
          (chat.sendMessage as ((m: unknown) => void) | undefined);
        if (typeof append !== "function") return;
        try {
          append({
            role: "user",
            content:
              "Muéstrame mis recordatorios pendientes con `preview_list` y dime cuáles debería atender primero.",
          });
        } catch {
          /* ignore */
        }
      }}
    />
  );
}

/**
 * Wraps the chat so the user can drop a PDF or image anywhere on it.
 *
 * Sprint C — multi-modal entry point. Drop a file:
 *  - PDF  → POST `/api/v1/integrations/pdf/parse` (returns parsed session)
 *  - image → POST `/api/v1/users/me/photo` (avatar) — note: a future iteration
 *    should let the agent decide what the image is for; for MVP we treat it
 *    as the profile photo, which is the only image upload we have wired.
 *
 * After upload, we inject a user message into the chat so the agent learns
 * about it and can react ("acabo de procesar tu CV, quieres importar X?").
 */
function ChatDropTarget({ children }: { children: React.ReactNode }) {
  const chat = useCopilotChat() as unknown as Record<string, unknown>;
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState<string | null>(null);
  const dragCount = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const onDragEnter = (e: DragEvent<HTMLDivElement>) => {
    if (!e.dataTransfer.types.includes("Files")) return;
    e.preventDefault();
    dragCount.current++;
    setDragOver(true);
  };
  const onDragLeave = () => {
    dragCount.current = Math.max(0, dragCount.current - 1);
    if (dragCount.current === 0) setDragOver(false);
  };
  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    if (e.dataTransfer.types.includes("Files")) {
      e.preventDefault();
    }
  };

  const inject = useCallback(
    (content: string) => {
      const append =
        (chat.appendMessage as ((m: unknown) => void) | undefined) ??
        (chat.sendMessage as ((m: unknown) => void) | undefined);
      if (typeof append !== "function") return;
      try {
        append({ role: "user", content });
      } catch {
        /* ignore — API moved between versions */
      }
    },
    [chat],
  );

  const injectAssistant = useCallback(
    (content: string) => {
      // Display-only: append an assistant message we received out-of-band
      // from the multimodal endpoint. We don't have a clean public API for
      // this in CopilotKit, so we use the same shape `appendMessage` accepts.
      const append =
        (chat.appendMessage as ((m: unknown) => void) | undefined) ??
        (chat.sendMessage as ((m: unknown) => void) | undefined);
      if (typeof append !== "function") return;
      try {
        append({ role: "assistant", content });
      } catch {
        /* ignore */
      }
    },
    [chat],
  );

  /** Common pipeline used by drag-drop and clipboard paste. */
  const processFiles = useCallback(
    async (files: File[], source: "drop" | "paste") => {
      if (files.length === 0) return;

      // Split by kind. Multimodal endpoint accepts up to 3 images per call;
      // PDFs go to the parse pipeline one at a time.
      const pdfs = files.filter((f) => f.type === "application/pdf");
      const imgs = files.filter((f) => f.type.startsWith("image/"));
      const rejected = files.filter(
        (f) => f.type !== "application/pdf" && !f.type.startsWith("image/"),
      );
      if (rejected.length) {
        toast.error(
          "Archivos no soportados",
          rejected.map((r) => r.name || "(sin nombre)").join(", "),
        );
      }
      if (pdfs.length === 0 && imgs.length === 0) return;

      // Per-file size guard — endpoint enforces too, but local rejection is faster.
      const tooBig = [...pdfs, ...imgs].find((f) => f.size > 10 * 1024 * 1024);
      if (tooBig) {
        toast.error("Archivo demasiado grande", `${tooBig.name || "archivo"} supera 10 MB.`);
        return;
      }
      if (imgs.length > 3) {
        toast.error(
          "Demasiadas imágenes",
          "Máximo 3 imágenes por mensaje. Sube el resto en otro turno.",
        );
        return;
      }

      const token = useAuthStore.getState().accessToken ?? "";
      setBusy(true);
      try {
        // --- PDFs (one POST each) -------------------------------------
        for (const file of pdfs) {
          const fd = new FormData();
          fd.append("file", file);
          const resp = await fetch("/api/v1/integrations/pdf/parse", {
            method: "POST",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: fd,
          });
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          toast.success("PDF procesado", file.name);
          inject(
            `He subido el PDF "${file.name}" a través del chat. Ya está parseado en una import-session. ¿Puedes revisarlo y proponerme qué entradas importar a mi universo?`,
          );
        }

        // --- Images (single multipart call, up to 3) ------------------
        if (imgs.length > 0) {
          const names = imgs
            .map((f, i) => f.name || `imagen_${i + 1}`)
            .join(", ");
          const verb = source === "paste" ? "He pegado" : "Adjunto";
          inject(
            imgs.length === 1
              ? `📎 ${verb}: ${imgs[0]!.name || "imagen del portapapeles"}`
              : `📎 ${verb} (${imgs.length}): ${names}`,
          );
          const fd = new FormData();
          const imgList =
            imgs.length === 1
              ? `la imagen "${imgs[0]!.name || "del portapapeles"}"`
              : `las ${imgs.length} imágenes (${names})`;
          fd.append(
            "text",
            [
              `He adjuntado ${imgList}. Para CADA imagen, clasifícala en UNA de estas categorías y extrae la información relevante:`,
              "",
              "- screenshot_oferta: captura/foto de una oferta de trabajo",
              "- linkedin_perfil: captura de perfil o experiencia de LinkedIn",
              "- diploma_certificacion: diploma, certificado o badge",
              "- foto_profesional: foto adecuada como avatar/CV",
              "- otra: cualquier otra cosa",
              "",
              "Responde EN TEXTO PLANO (sin invocar tools de propose_*) con esta estructura POR CADA imagen:",
              "",
              "── IMAGEN <índice>: <nombre> ──",
              "CATEGORÍA: <una de las anteriores>",
              "RESUMEN: <2-3 líneas describiendo qué contiene>",
              "DATOS_EXTRAÍDOS:",
              "- <bullets con los datos concretos>",
              "PRÓXIMA ACCIÓN SUGERIDA: <qué tool propose_* invocaríamos en el siguiente turno>",
              "",
              "En el turno siguiente te pediré que avances con las acciones.",
            ].join("\n"),
          );
          for (const f of imgs) fd.append("images", f);
          setPhase("Analizando imagen…");
          const reply = await streamMultimodal(fd, token, {
            onToolStart: (name) => setPhase(phaseForTool(name)),
            onToolEnd: () => setPhase("Generando respuesta…"),
            onChunk: () => setPhase("Generando respuesta…"),
          });
          if (reply.trim()) injectAssistant(reply);
          toast.success(
            imgs.length === 1 ? "Imagen procesada" : `${imgs.length} imágenes procesadas`,
            names,
          );
        }
      } catch (err) {
        toast.error("Subida fallida", (err as Error).message);
      } finally {
        setBusy(false);
        setPhase(null);
      }
    },
    [inject, injectAssistant],
  );

  const onDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    dragCount.current = 0;
    setDragOver(false);
    const files = Array.from(e.dataTransfer?.files ?? []);
    if (files.length === 0) return;
    await processFiles(files, "drop");
  };

  /** Ctrl+V / Cmd+V — pick up any image items in the clipboard. We don't
   *  interfere with text paste: if the clipboard has no image items, the
   *  original event proceeds normally and the chat textarea handles it. */
  const onPaste = async (e: React.ClipboardEvent<HTMLDivElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    const imgs: File[] = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i]!;
      if (item.kind !== "file") continue;
      if (!item.type.startsWith("image/")) continue;
      const f = item.getAsFile();
      if (f) {
        // Clipboard images come without a meaningful name; synthesise one
        // so downstream prompts and toasts have something to show.
        if (!f.name || f.name === "image.png" || f.name === "blob") {
          const ext = f.type.split("/")[1] || "png";
          const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
          imgs.push(new File([f], `pegado-${ts}.${ext}`, { type: f.type }));
        } else {
          imgs.push(f);
        }
      }
    }
    if (imgs.length === 0) return; // pass-through for text paste
    e.preventDefault();
    await processFiles(imgs, "paste");
  };

  return (
    <div
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onPaste={onPaste}
      className="relative h-full"
    >
      {children}

      {/* Floating attach button — primary entry on mobile (no drag), still
          usable on desktop. Hidden while busy or while the user is dragging. */}
      {!busy && !dragOver && (
        <>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,image/jpeg,image/png,image/webp,image/gif"
            multiple
            className="sr-only"
            onChange={async (e) => {
              const files = Array.from(e.target.files ?? []);
              // Reset so re-picking the same file fires onChange again.
              e.target.value = "";
              if (files.length) await processFiles(files, "drop");
            }}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            aria-label="Adjuntar archivo"
            title="Adjuntar PDF o imagen (también puedes arrastrar o pegar)"
            className="chat-attach-btn absolute bottom-24 right-4 md:bottom-20 md:right-6 z-20 inline-flex items-center justify-center w-11 h-11 rounded-full bg-canvas border border-hairline shadow-soft text-ink hover:bg-surface hover:-translate-y-[1px] active:translate-y-0 transition-all duration-180 ease-pirsch"
          >
            <Paperclip size={16} />
          </button>
        </>
      )}
      {(dragOver || busy) && (
        <div
          aria-live="polite"
          className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center bg-leaf-soft/70 backdrop-blur-sm rounded-card border-2 border-dashed border-leaf"
        >
          <div className="flex flex-col items-center gap-2 text-leaf-ink">
            {busy ? (
              <Loader2 size={28} className="animate-spin" />
            ) : (
              <FileUp size={28} />
            )}
            <span className="text-sm font-medium">
              {busy ? phase ?? "Subiendo…" : "Suelta para procesar"}
            </span>
            <span className="text-xs text-leaf-ink/80">
              PDF o imagen (hasta 3 imágenes), 10 MB cada uno
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

interface RehydratedMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt?: string;
}

/**
 * Loads the user's persisted conversation from the AG-UI scroll-back endpoint
 * and seeds `useCopilotChat().setMessages` with it. Runs once per mount.
 *
 * The endpoint returns at most the last N messages (default 80) extracted
 * from `ai.agno_sessions.runs` — Agno's own persistence. If the call fails
 * or the user is unauthenticated, we silently fall back to an empty chat.
 */
function ChatRehydrator() {
  const chat = useCopilotChat() as unknown as Record<string, unknown>;
  const userId = useAuthStore((s) => s.userId);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    if (!userId) return;
    const setMessages = chat.setMessages as
      | ((m: unknown[]) => void)
      | undefined;
    if (typeof setMessages !== "function") return;

    ran.current = true;
    const threadId = `main-${userId}`;
    void api<{ messages: RehydratedMessage[]; nextCursor: string | null }>(
      `/agui/threads/${threadId}/messages?limit=80`,
    )
      .then((resp) => {
        if (!resp?.messages?.length) return;
        try {
          setMessages(
            resp.messages.map((m) => ({
              id: m.id,
              role: m.role,
              content: m.content,
              createdAt: m.createdAt,
            })),
          );
        } catch {
          /* ignore — CopilotKit may reject some message shapes between versions */
        }
      })
      .catch(() => {
        // Endpoint optional; empty chat on failure is fine.
      });
  }, [userId, chat]);

  return null;
}

/** Friendly Spanish label for a server-side tool the agent is using.
 *  Falls back to the raw name if we don't have a mapping. */
function phaseForTool(name: string): string {
  const map: Record<string, string> = {
    get_universe_summary: "Leyendo tu universo…",
    find_gaps: "Detectando huecos…",
    search_universe: "Buscando en tu universo…",
    find_existing: "Comprobando duplicados…",
    list_jobs: "Consultando tus ofertas…",
    list_documents: "Consultando tus documentos…",
    get_preferences: "Leyendo tus preferencias…",
    list_reminders: "Leyendo tus reminders…",
    get_integrations_status: "Comprobando integraciones…",
    get_tier: "Comprobando tu plan…",
    compute_job_match: "Calculando match…",
    search_knowledge: "Buscando en knowledge…",
    list_notes: "Leyendo tus notas…",
    get_change_history: "Consultando historial…",
  };
  return map[name] ?? `Usando ${name.replace(/_/g, " ")}…`;
}

interface StreamMultimodalCallbacks {
  /** Called when the agent starts using a server-side tool (search_universe,
   *  list_jobs, …). Useful to show "Consultando tu universo…" in the UI. */
  onToolStart?: (name: string) => void;
  /** Called when the tool finishes. Pair with `onToolStart` to clear the hint. */
  onToolEnd?: (name: string) => void;
  /** Called with each text chunk as it arrives — for live token rendering.
   *  The full text is also returned by the promise on success. */
  onChunk?: (delta: string) => void;
}

/**
 * POST a multipart form to the multimodal endpoint and accumulate the SSE
 * stream into a single assistant string. Returns the full text once the
 * stream emits `{type:"done"}` or throws on `{type:"error"}`. Optional
 * callbacks let the caller react to tool usage and incremental chunks.
 */
async function streamMultimodal(
  fd: FormData,
  token: string,
  cb: StreamMultimodalCallbacks = {},
): Promise<string> {
  const resp = await fetch(
    "/agui/agent/universe_coordinator/run-multimodal",
    {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    },
  );
  if (!resp.ok || !resp.body) {
    const detail = await resp.text().catch(() => "");
    throw new Error(`HTTP ${resp.status}: ${detail.slice(0, 120)}`);
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let assembled = "";
  // SSE frames are `data: <json>\n\n`. Buffer until we see \n\n.
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 2);
      if (!frame.startsWith("data:")) continue;
      const json = frame.slice(5).trim();
      if (!json) continue;
      try {
        const ev = JSON.parse(json) as
          | { type: "chunk"; content: string }
          | { type: "tool-start"; name: string }
          | { type: "tool-end"; name: string }
          | { type: "done"; run_id: string | null }
          | { type: "error"; message: string };
        if (ev.type === "chunk") {
          assembled += ev.content;
          cb.onChunk?.(ev.content);
        } else if (ev.type === "tool-start") cb.onToolStart?.(ev.name);
        else if (ev.type === "tool-end") cb.onToolEnd?.(ev.name);
        else if (ev.type === "error") throw new Error(ev.message);
        else if (ev.type === "done") return assembled;
      } catch (parseErr) {
        // Malformed line — skip but keep going.
        if (parseErr instanceof Error && parseErr.message.length) {
          // Don't swallow agent-side errors emitted as `{type: "error"}`.
          if (parseErr.message !== "Unexpected token") throw parseErr;
        }
      }
    }
  }
  return assembled;
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
      const append =
        (chat.appendMessage as ((m: unknown) => void) | undefined) ??
        (chat.sendMessage as ((m: unknown) => void) | undefined);
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
