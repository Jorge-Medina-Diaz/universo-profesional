import { useEffect, useRef, useState } from "react";
import { MessageCircle, Send, Sparkles } from "lucide-react";

import { publicTwin } from "@/shared/api";

interface Turn {
  role: "user" | "assistant";
  content: string;
}

export interface TwinChatLabels {
  emptyHint: string;
  placeholder: string;
  placeholderDone: string;
  thinking: string;
  sendError: string;
  budgetError: string;
  softCapCta?: string;
  replayBanner?: string;
  offlineBanner?: string;
}

const DEFAULT_LABELS: TwinChatLabels = {
  emptyHint: "Pregúntale lo que quieras sobre su trayectoria profesional.",
  placeholder: "Escribe tu pregunta…",
  placeholderDone: "Conversación completada",
  thinking: "Pensando…",
  sendError: "No se pudo enviar el mensaje. Inténtalo de nuevo.",
  budgetError: "Este perfil ha alcanzado su límite de conversación por hoy.",
};

/** A scripted fallback so the demo NEVER dies silently (budget/offline). */
export interface TwinReplay {
  turns: Turn[];
}

/**
 * The one twin chat core — used by the public page (#/t/{slug}), the
 * ?embed=1 iframe widget and the landing's live demo. Stateless server:
 * history is client-carried; `softCapTurns` swaps the composer for a CTA
 * after N user turns (landing conversion moment).
 */
export function TwinChatCard({
  slug,
  suggested,
  labels: labelsProp,
  height = "h-[420px]",
  softCapTurns,
  onSoftCap,
  fallbackReplay,
  onActivity,
}: {
  slug: string;
  suggested: string[];
  labels?: Partial<TwinChatLabels>;
  height?: string;
  /** after N user turns, swap composer for the CTA (softCapCta label) */
  softCapTurns?: number;
  onSoftCap?: () => void;
  /** labeled replay shown when the live demo is over budget / unreachable */
  fallbackReplay?: TwinReplay;
  /** notifies the parent on each state change (for ambient choreography) */
  onActivity?: (state: "thinking" | "answered" | "error") => void;
}) {
  const labels = { ...DEFAULT_LABELS, ...labelsProp };
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limitReached, setLimitReached] = useState(false);
  const [replayMode, setReplayMode] = useState<"none" | "budget" | "offline">("none");
  const sessionRef = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const userTurns = turns.filter((t) => t.role === "user").length;
  const softCapped = softCapTurns != null && userTurns >= softCapTurns;

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [turns, sending]);

  useEffect(() => {
    if (softCapped) onSoftCap?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [softCapped]);

  const enterReplay = (mode: "budget" | "offline") => {
    if (!fallbackReplay) return false;
    setReplayMode(mode);
    setTurns(fallbackReplay.turns);
    return true;
  };

  const ask = async (message: string) => {
    const text = message.trim();
    if (!text || sending || limitReached || softCapped || replayMode !== "none") return;
    setError(null);
    setSending(true);
    setInput("");
    setTurns((t) => [...t, { role: "user", content: text }]);
    onActivity?.("thinking");
    try {
      const res = await publicTwin.chat(slug, {
        message: text,
        history: turns.slice(-12),
        session_id: sessionRef.current,
      });
      sessionRef.current = res.session_id ?? sessionRef.current;
      setTurns((t) => [...t, { role: "assistant", content: res.answer }]);
      if (res.limit_reached) setLimitReached(true);
      onActivity?.("answered");
    } catch (e) {
      onActivity?.("error");
      const msg = e instanceof Error ? e.message : "";
      const isBudget = msg.includes("429") || msg.includes("límite");
      if (enterReplay(isBudget ? "budget" : "offline")) {
        setSending(false);
        return;
      }
      setError(isBudget ? labels.budgetError : labels.sendError);
      setTurns((t) => t.slice(0, -1));
      setInput(text);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col rounded-2xl border border-hairline bg-surface/60 overflow-hidden shadow-soft">
      {replayMode !== "none" && (
        <div
          role="status"
          className="px-4 py-2 text-[11px] font-mono bg-sunbeam-soft text-ink border-b border-hairline"
        >
          {replayMode === "budget" ? labels.replayBanner : labels.offlineBanner}
        </div>
      )}
      <div
        ref={scrollRef}
        className={`overflow-y-auto px-4 py-4 flex flex-col gap-3 ${height}`}
      >
        {turns.length === 0 && (
          <div className="m-auto text-center max-w-sm">
            <MessageCircle size={22} className="mx-auto mb-2 text-stone" aria-hidden />
            <p className="text-sm text-stone mb-4">{labels.emptyHint}</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {suggested.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => void ask(q)}
                  className="text-xs px-3 py-1.5 rounded-full border border-hairline bg-canvas text-ink hover:bg-surface transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {turns.map((t, i) => (
          <div
            key={i}
            className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm whitespace-pre-wrap ${
              t.role === "user"
                ? "self-end bg-nova/15 text-ink"
                : "self-start bg-canvas border border-hairline text-ink"
            }`}
          >
            {t.content}
          </div>
        ))}
        {sending && (
          <div className="self-start text-xs text-stone animate-pulse px-2">
            {labels.thinking}
          </div>
        )}
        {error && (
          <div
            role="alert"
            className="self-center text-xs text-danger bg-danger-soft border border-danger/30 rounded-lg px-3 py-2"
          >
            {error}
          </div>
        )}
      </div>
      {softCapped && labels.softCapCta ? (
        <a
          href="#/register"
          className="flex items-center justify-center gap-2 border-t border-hairline bg-sunbeam text-ink font-medium text-sm px-3 py-3 hover:opacity-90 transition-opacity"
        >
          <Sparkles size={14} aria-hidden /> {labels.softCapCta}
        </a>
      ) : (
        <form
          className="flex items-center gap-2 border-t border-hairline bg-canvas px-3 py-2.5"
          onSubmit={(e) => {
            e.preventDefault();
            void ask(input);
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            maxLength={600}
            disabled={sending || limitReached || replayMode !== "none"}
            placeholder={limitReached ? labels.placeholderDone : labels.placeholder}
            aria-label={labels.placeholder}
            className="flex-1 bg-transparent text-sm text-ink placeholder:text-stone outline-none disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || sending || limitReached || replayMode !== "none"}
            aria-label="Enviar"
            className="h-8 w-8 grid place-items-center rounded-full bg-nova text-white disabled:opacity-40 transition-opacity"
          >
            <Send size={14} />
          </button>
        </form>
      )}
    </div>
  );
}
