/**
 * Contextual suggestion chips above the composer.
 *
 * Surfaces one-tap prompts based on the current app state:
 * latest job, pending reminders, missing integrations, etc.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText, BellRing, Link2, Sparkles, Compass, Mic } from "lucide-react";
import { queryKeys } from "@/shared/queryKeys";
import { universe, useAuthStore } from "@/shared/api";
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

  if (suggestions.length === 0) return null;

  return (
    <div className="composer-suggestions">
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
