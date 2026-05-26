/**
 * Contextual suggestion chips above the composer.
 *
 * Surfaces one-tap prompts based on the current app state:
 * latest job, pending reminders, missing integrations, etc.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText, BellRing, Link2, Sparkles } from "lucide-react";
import { queryKeys } from "@/shared/queryKeys";
import { universe, useAuthStore } from "@/shared/api";


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
  }, [jobsQ.data, remindersQ.data]);

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
