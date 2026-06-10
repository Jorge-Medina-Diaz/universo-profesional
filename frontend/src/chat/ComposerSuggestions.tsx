/**
 * Contextual suggestion chips above the composer.
 *
 * Surfaces one-tap prompts based on the current app state:
 * latest job, pending reminders, missing integrations, etc.
 */
import { useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, BellRing, Link2, Sparkles, Compass, Mic, X } from "lucide-react";
import { queryKeys } from "@/shared/queryKeys";
import { universe, nudges, useAuthStore, type NudgeRow, type NudgeAckAction } from "@/shared/api";
import { toast } from "@/ui";
import { useChatState } from "./state";


export interface ComposerSuggestion {
  id: string;
  label: string;
  prompt: string;
  icon: React.ReactNode;
}

interface Props {
  onSelect: (s: ComposerSuggestion) => void;
}

export function ComposerSuggestions({ onSelect }: Props) {
  const authed = !!useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  // The currently-focused entity (set when the user taps a graph node →
  // "talk about", or by the agent's set_chat_focus). Drives a contextual chip
  // so the composer is proactive about what the user is looking at.
  const focusMeta = useChatState((s) => s.meta);
  const focusLabel = typeof focusMeta?.label === "string" ? focusMeta.label : null;

  const jobsQ = useQuery({
    queryKey: queryKeys.jobs.all,
    queryFn: () => universe.list("jobs"),
    enabled: authed,
    staleTime: 5 * 60_000,
  });

  const remindersQ = useQuery({
    queryKey: queryKeys.reminders.pending,
    queryFn: () => universe.reminders.list(),
    enabled: authed,
    staleTime: 5 * 60_000,
  });

  // Proactive server-computed nudges (Phase 3) — each renders as its own chip
  // with an explicit dismiss affordance; accepting one seeds its prompt into
  // the thread via the pendingInjection channel and acks it as 'acted'.
  const nudgesQ = useQuery({
    queryKey: queryKeys.nudges.active,
    queryFn: () => nudges.active(),
    enabled: authed,
    staleTime: 5 * 60_000,
  });
  const activeNudges = (nudgesQ.data?.nudges ?? []).filter(
    (n) => typeof n.payload?.chip === "string" && n.payload.chip.trim() !== "",
  );

  const ackNudge = async (id: string, action: NudgeAckAction) => {
    try {
      await nudges.ack(id, action);
    } catch (e) {
      toast.error("No se pudo actualizar el aviso", (e as Error).message);
    } finally {
      // Refetch regardless — on failure the chip reappears (server truth).
      void qc.invalidateQueries({ queryKey: queryKeys.nudges.active });
    }
  };

  const acceptNudge = (n: NudgeRow) => {
    const prompt =
      typeof n.payload?.prompt === "string" && n.payload.prompt.trim()
        ? n.payload.prompt
        : n.payload.chip;
    useChatState.getState().setPendingInjection({ content: prompt });
    void ackNudge(n.id, "acted");
  };

  const suggestions = useMemo<ComposerSuggestion[]>(() => {
    const list: ComposerSuggestion[] = [];

    // Contextual chip about the focused entity takes priority.
    if (focusLabel) {
      list.push({
        id: "focus-explore",
        label: `Profundiza en ${focusLabel}`,
        prompt: `Cuéntame más sobre ${focusLabel}: qué tengo registrado, cómo se conecta con el resto de mi universo y qué me falta relacionado.`,
        icon: <Compass size={12} />,
      });
    }

    // Proactive: an upcoming interview is a high-signal, time-sensitive trigger
    // — surface prep before the user thinks to ask (proactive agentic UI).
    const interviewingJob = (jobsQ.data ?? []).find(
      (j) => (j as { status?: string }).status === "interviewing",
    ) as { title?: string; company_name?: string } | undefined;
    if (interviewingJob) {
      const name = interviewingJob.title ?? interviewingJob.company_name ?? "tu próxima entrevista";
      list.push({
        id: "interview-prep",
        label: `Prepara tu entrevista: ${name}`,
        prompt: `Prepárame para la entrevista de ${name}: brief de la empresa, preguntas probables y mis respuestas STAR ancladas en mi universo.`,
        icon: <Mic size={12} />,
      });
    }

    const latestJob = (jobsQ.data ?? []).slice().sort(
      (a, b) => new Date((b as { created_at?: string }).created_at ?? 0).getTime() -
                new Date((a as { created_at?: string }).created_at ?? 0).getTime()
    )[0] as { title?: string; company_name?: string } | undefined;

    if (latestJob) {
      const name = latestJob.title ?? latestJob.company_name ?? "esta oferta";
      list.push({
        id: "cv-job",
        label: `Generar CV para ${name}`,
        prompt: `Genera un CV optimizado para la oferta: ${name}`,
        icon: <FileText size={12} />,
      });
    }

    const remindersCount = remindersQ.data?.length ?? 0;
    if (remindersCount > 0) {
      list.push({
        id: "reminders",
        label: `Revisar ${remindersCount} recordatorio${remindersCount > 1 ? "s" : ""} pendiente${remindersCount > 1 ? "s" : ""}`,
        prompt: "Muéstrame mis recordatorios pendientes y cuáles debería atender primero.",
        icon: <BellRing size={12} />,
      });
    }

    list.push({
      id: "sync-linkedin",
      label: "Sincronizar LinkedIn",
      prompt: "Ayúdame a sincronizar mi perfil de LinkedIn.",
      icon: <Link2 size={12} />,
    });

    if (list.length === 0) {
      list.push({
        id: "help",
        label: "¿Qué puedes hacer?",
        prompt: "¿Qué puedes hacer por mí?",
        icon: <Sparkles size={12} />,
      });
    }

    return list.slice(0, 3);
  }, [jobsQ.data, remindersQ.data, focusLabel]);

  if (suggestions.length === 0 && activeNudges.length === 0) return null;

  return (
    <div className="composer-suggestions">
      {activeNudges.map((n) => (
        // Not a <button> wrapper: the dismiss ✕ lives INSIDE the chip and
        // nested buttons are invalid HTML — so the chip is a group of two.
        <div key={n.id} role="group" className="composer-suggestion-chip">
          <button
            type="button"
            onClick={() => acceptNudge(n)}
            className="inline-flex min-w-0 items-center gap-[5px]"
          >
            <span className="composer-suggestion-chip__icon">
              <Sparkles size={12} />
            </span>
            <span className="composer-suggestion-chip__label truncate">
              {n.payload.chip}
            </span>
          </button>
          <button
            type="button"
            onClick={() => void ackNudge(n.id, "dismissed")}
            aria-label="Descartar sugerencia"
            title="Descartar"
            className="-mr-1 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full opacity-50 transition-opacity hover:opacity-100"
          >
            <X size={11} />
          </button>
        </div>
      ))}
      {suggestions.map((s) => (
        <button
          key={s.id}
          type="button"
          onClick={() => onSelect(s)}
          className="composer-suggestion-chip"
        >
          <span className="composer-suggestion-chip__icon">{s.icon}</span>
          <span className="composer-suggestion-chip__label">{s.label}</span>
        </button>
      ))}
    </div>
  );
}
