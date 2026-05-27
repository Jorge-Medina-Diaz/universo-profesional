/**
 * Custom chat surface for CopilotKit — replaces the default boxy message list
 * with an editorial "conversation with your universe" treatment.
 *
 * These components are passed to `<CopilotChat AssistantMessage UserMessage
 * Input />`, so ALL of CopilotKit's plumbing is preserved: token streaming,
 * scroll-back, and — critically — HITL cards, which arrive via
 * `message.generativeUI()` and are rendered inside {@link AgentMessage}.
 *
 * Design language: the agent is a distinct presence (a constellation orb), its
 * replies flow as typographic prose on the canvas (no chat-bubble box), and the
 * user's turns are warm ink bubbles on the right. Motion is restrained — one
 * entrance rise per message, a calm thinking pulse.
 */
import { useRef, useState, useCallback, memo } from "react";
import { Markdown } from "@copilotkit/react-ui";
import type {
  AssistantMessageProps,
  UserMessageProps,
  InputProps,
  ErrorMessageProps,
  ImageRendererProps,
} from "@copilotkit/react-ui";
import {
  AlertTriangle,
  ArrowUp,
  Check,
  Copy,
  FileText,
  Paperclip,
  RotateCcw,
  Sparkles,
  Square,
} from "lucide-react";
import { cn } from "@/ui";
import { useThrottledText } from "./useThrottledText";
import { ThinkingSteps, useHeuristicThinkingSteps } from "./ThinkingSteps";
import { InlineEntityEditor } from "./InlineEntityEditor";
import { CommandPalette, type SlashCommand, type CommandPaletteHandle } from "./CommandPalette";
import { ComposerSuggestions, type ComposerSuggestion } from "./ComposerSuggestions";

/**
 * In CopilotKit 1.57 a message's `content` is `string | InputContent[]` (text +
 * image/document parts). Older code assumed a string and rendered nothing for
 * arrays, which made user/assistant bubbles vanish. These helpers normalise it.
 */
type ContentPart = {
  type?: string;
  text?: string;
  source?: (ImageRendererProps["source"] & { mimeType?: string }) | undefined;
  name?: string;
  filename?: string;
  metadata?: { name?: string; filename?: string } | undefined;
};

function messageText(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return (content as ContentPart[])
      .filter((p) => p && typeof p === "object" && p.type === "text")
      .map((p) => p.text ?? "")
      .join("");
  }
  return "";
}

function imageParts(content: unknown): ContentPart[] {
  if (!Array.isArray(content)) return [];
  return (content as ContentPart[]).filter(
    (p) => p && typeof p === "object" && p.type === "image" && !!p.source,
  );
}

/** Non-image, non-text attachment parts (PDFs, docs) so they show as chips. */
function docParts(content: unknown): ContentPart[] {
  if (!Array.isArray(content)) return [];
  return (content as ContentPart[]).filter(
    (p) =>
      p &&
      typeof p === "object" &&
      !!p.source &&
      p.type !== "image" &&
      p.type !== "text",
  );
}

/** Best-effort display name for an attachment chip. */
function docLabel(p: ContentPart): string {
  const name =
    p.name ?? p.filename ?? p.metadata?.name ?? p.metadata?.filename ?? "";
  if (name) return name;
  const mime = p.source?.mimeType ?? "";
  if (mime.includes("pdf")) return "Documento PDF";
  if (mime) return mime.split("/").pop() || "Documento";
  return "Documento adjunto";
}

/** The agent's avatar — a small glowing constellation orb. */
function AgentOrb({ thinking = false }: { thinking?: boolean }) {
  return (
    <span
      aria-hidden
      className={cn("agent-orb", thinking && "agent-orb--thinking")}
    >
      <Sparkles size={12} strokeWidth={2.25} className="agent-orb__spark" />
    </span>
  );
}

/** Calm three-dot pulse shown while the agent is thinking (no content yet). */
function ThinkingDots() {
  return (
    <div className="flex items-center gap-2 pt-1.5" aria-label="El agente está pensando">
      <span className="thinking-dots">
        <i /> <i /> <i />
      </span>
      <span className="text-xs text-stone/80">Pensando…</span>
    </div>
  );
}

export const AgentMessage = memo(function AgentMessage({
  message,
  isLoading,
  isGenerating,
  onRegenerate,
}: AssistantMessageProps) {
  const raw = messageText(message?.content);
  const content = raw.trim() ? raw : "";
  const throttledContent = useThrottledText(content, 50);
  const displayContent = isGenerating ? throttledContent : content;
  const card = message?.generativeUI?.() ?? undefined;
  const thinking = !!isLoading && !content;
  const [copied, setCopied] = useState(false);

  const steps = useHeuristicThinkingSteps(content, !!isGenerating);

  const handleInlineEdit = useCallback((original: string, corrected: string) => {
    // Emit a user-visible correction into the chat thread via a custom event
    // that CopilotSurface can listen to and inject as a user message.
    window.dispatchEvent(
      new CustomEvent("cvs-chat-inline-edit", {
        detail: { original, corrected },
      }),
    );
  }, []);

  // Suppressed/empty assistant turns (e.g. route hand-offs) render nothing —
  // no lone orb for a whitespace-only coordinator message.
  if (!content && !card && !thinking) return null;

  const copy = () => {
    if (!displayContent) return;
    void navigator.clipboard?.writeText(displayContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="agent-msg group flex gap-3 px-1 py-2">
      <AgentOrb thinking={thinking || (!!isGenerating && steps.some((s) => s.status === "active"))} />
      <div className="min-w-0 flex-1">
        {thinking ? (
          <ThinkingDots />
        ) : (
          <>
            {!!isGenerating && steps.some((s) => s.status !== "pending") && (
              <ThinkingSteps steps={steps} className="mb-1.5" />
            )}
            {displayContent && (
              <div className={cn("agent-prose", isGenerating && "agent-prose--streaming")}>
                <InlineEntityEditor onEdit={handleInlineEdit}>
                  <Markdown content={displayContent} />
                </InlineEntityEditor>
              </div>
            )}
            {card && <div className="mt-1.5">{card}</div>}
            {displayContent && !isGenerating && (
              <div className="agent-actions mt-1 flex items-center gap-0.5 opacity-0 transition-opacity duration-200 group-hover:opacity-100 focus-within:opacity-100">
                <button
                  type="button"
                  onClick={copy}
                  aria-label="Copiar"
                  className="agent-action-btn"
                >
                  {copied ? <Check size={13} /> : <Copy size={13} />}
                </button>
                {onRegenerate && (
                  <button
                    type="button"
                    onClick={() => onRegenerate()}
                    aria-label="Regenerar respuesta"
                    className="agent-action-btn"
                  >
                    <RotateCcw size={13} />
                  </button>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
});

export const PersonMessage = memo(function PersonMessage({ message, ImageRenderer }: UserMessageProps) {
  const content = messageText(message?.content);
  const imgs = imageParts(message?.content);
  const docs = docParts(message?.content);
  // Never render nothing for a real turn — attachments-only messages must show.
  if (!content && imgs.length === 0 && docs.length === 0) return null;
  return (
    <div className="flex justify-end px-1 py-2">
      <div className="flex max-w-[85%] flex-col items-end gap-2">
        {imgs.length > 0 && (
          <div className="flex flex-wrap justify-end gap-2">
            {imgs.map((p, i) => (
              <div
                key={i}
                className="overflow-hidden rounded-card border border-hairline max-w-[220px]"
              >
                {ImageRenderer ? <ImageRenderer source={p.source} /> : null}
              </div>
            ))}
          </div>
        )}
        {docs.length > 0 && (
          <div className="flex flex-wrap justify-end gap-2">
            {docs.map((p, i) => (
              <div
                key={i}
                className="inline-flex items-center gap-2 rounded-card border border-hairline bg-surface px-3 py-2 max-w-[260px]"
              >
                <span className="grid place-items-center w-7 h-7 shrink-0 rounded-md bg-canvas text-ink">
                  <FileText size={15} strokeWidth={2} />
                </span>
                <span className="text-xs text-ink/80 truncate">{docLabel(p)}</span>
              </div>
            ))}
          </div>
        )}
        {content && <div className="person-bubble">{content}</div>}
      </div>
    </div>
  );
});

/**
 * Inline, in-thread error bubble for genuine run/transport failures (RUN_ERROR,
 * connect failures). Agent "no output" failures (e.g. no credit) are surfaced by
 * the backend as a normal assistant message instead, so the user's turn persists.
 */
export function ErrorMessage({ error }: ErrorMessageProps) {
  const raw =
    typeof error === "string"
      ? error
      : String((error as { message?: string } | undefined)?.message ?? "");
  const lower = raw.toLowerCase();
  let title = "El agente tuvo un problema";
  let detail = raw.slice(0, 200) || "Inténtalo de nuevo en un momento.";
  if (/credit|quota|rate.?limit|429|billing|overloaded|sin crédito|no disponible/.test(lower)) {
    title = "El agente no está disponible ahora";
    detail =
      "El servicio de IA se quedó sin crédito o superó su límite. Inténtalo de nuevo en un rato.";
  } else if (/failed to fetch|network|connect|timeout|econn/.test(lower)) {
    title = "No pude conectar con tu agente";
    detail = "Comprueba tu conexión o que el servidor esté activo, e inténtalo de nuevo.";
  }
  return (
    <div className="agent-msg flex gap-3 px-1 py-2">
      <span
        aria-hidden
        className="grid place-items-center w-7 h-7 shrink-0 rounded-full bg-red-50 text-red-700"
      >
        <AlertTriangle size={13} strokeWidth={2.25} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="rounded-card border border-red-200 bg-red-50/60 px-3.5 py-2.5">
          <div className="text-sm font-medium text-red-800 leading-tight">{title}</div>
          <div className="mt-0.5 text-xs leading-relaxed text-red-700/90">{detail}</div>
        </div>
      </div>
    </div>
  );
}

export const Composer = memo(function Composer({
  inProgress,
  onSend,
  onStop,
  onUpload,
  hideStopButton,
  chatReady,
}: InputProps) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  const paletteRef = useRef<CommandPaletteHandle>(null);
  const disabled = chatReady === false;
  const showPalette = text.startsWith("/");

  const autoGrow = () => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const reset = () => {
    setText("");
    requestAnimationFrame(() => {
      if (ref.current) ref.current.style.height = "auto";
    });
  };

  const send = useCallback((value: string) => {
    const t = value.trim();
    if (!t || inProgress || disabled) return;
    reset();
    void onSend(t);
  }, [inProgress, disabled, onSend]);

  const handleSelectCommand = useCallback((cmd: SlashCommand) => {
    setText(cmd.prompt);
    requestAnimationFrame(() => {
      autoGrow();
      ref.current?.focus();
    });
  }, []);

  const handleSelectSuggestion = useCallback((s: ComposerSuggestion) => {
    send(s.prompt);
  }, [send]);

  return (
    <div className="composer-wrap">
      {!showPalette && !inProgress && (
        <ComposerSuggestions onSelect={handleSelectSuggestion} />
      )}
      <div className="composer group relative">
        {onUpload && (
          <button
            type="button"
            onClick={() => onUpload()}
            disabled={disabled}
            aria-label="Adjuntar imagen o PDF"
            title="Adjuntar imagen o PDF"
            className="composer-attach shrink-0 self-end inline-flex items-center justify-center w-9 h-9 rounded-full text-stone hover:text-ink hover:bg-surface/70 transition-colors duration-180 disabled:opacity-40 disabled:pointer-events-none"
          >
            <Paperclip size={16} />
          </button>
        )}
        <textarea
          ref={ref}
          rows={1}
          value={text}
          disabled={disabled}
          placeholder={disabled ? "Conectando…" : "Escribe a tu agente…"}
          onChange={(e) => {
            setText(e.target.value);
            autoGrow();
          }}
          onKeyDown={(e) => {
            if (paletteRef.current?.isOpen) {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                paletteRef.current.moveDown();
                return;
              }
              if (e.key === "ArrowUp") {
                e.preventDefault();
                paletteRef.current.moveUp();
                return;
              }
              if (e.key === "Enter") {
                e.preventDefault();
                paletteRef.current.selectActive();
                return;
              }
              if (e.key === "Escape") {
                paletteRef.current.close();
                return;
              }
              return;
            }
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(text);
            }
          }}
          className="composer-input"
        />
        {inProgress && !hideStopButton ? (
          <button
            type="button"
            onClick={() => onStop?.()}
            aria-label="Detener"
            className="composer-stop"
          >
            <Square size={13} strokeWidth={2.5} className="fill-current" />
          </button>
        ) : (
          <button
            type="button"
            onClick={() => send(text)}
            disabled={!text.trim() || inProgress || disabled}
            aria-label="Enviar"
            className="composer-send"
          >
            <ArrowUp size={17} strokeWidth={2.5} />
          </button>
        )}
        <CommandPalette
          ref={paletteRef}
          query={text}
          onSelect={handleSelectCommand}
          onClose={() => {
            setText("");
            ref.current?.focus();
          }}
        />
      </div>
      <p className="composer-hint hidden sm:block">
        <kbd>Enter</kbd> para enviar · <kbd>Shift</kbd>+<kbd>Enter</kbd> salto de línea · <kbd>/</kbd> comandos
      </p>
    </div>
  );
});
