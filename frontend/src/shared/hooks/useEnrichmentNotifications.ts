import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "@/ui";
import { api } from "@/shared/api";

interface UniverseSummary {
  counts: {
    educations: number;
    experiences: number;
    projects: number;
    skills: number;
    languages: number;
  };
}

const SUMMARY_POLL_INTERVAL = 10_000; // 10s

/**
 * Polls the universe summary and shows a toast when new entities
 * are detected (e.g. after auto-enrichment from a chat message).
 */
export function useEnrichmentNotifications() {
  const lastCountsRef = useRef<Record<string, number> | null>(null);
  const toastShownRef = useRef<Set<string>>(new Set());

  const { data: summary } = useQuery<UniverseSummary>({
    queryKey: ["universe", "summary"],
    queryFn: async () => {
      return api<UniverseSummary>("/api/v1/universe/summary");
    },
    refetchInterval: SUMMARY_POLL_INTERVAL,
    staleTime: 5_000,
  });

  useEffect(() => {
    if (!summary) return;

    const counts = summary.counts;
    const prev = lastCountsRef.current;
    lastCountsRef.current = { ...counts };

    if (!prev) return; // first load — don't toast

    const deltas: string[] = [];
    (Object.keys(counts) as Array<keyof typeof counts>).forEach((key) => {
      const delta = counts[key] - (prev[key] ?? 0);
      if (delta > 0) {
        const label =
          {
            educations: "formación",
            experiences: "experiencia",
            projects: "proyecto",
            skills: "skill",
            languages: "idioma",
          }[key] ?? key;
        deltas.push(`${delta} ${label}${delta > 1 ? "s" : ""}`);
      }
    });

    if (deltas.length === 0) return;

    const toastKey = deltas.join(",");
    if (toastShownRef.current.has(toastKey)) return;
    toastShownRef.current.add(toastKey);

    // Keep only last 20 keys to avoid unbounded growth
    if (toastShownRef.current.size > 20) {
      const iter = toastShownRef.current.values();
      toastShownRef.current.delete(iter.next().value!);
    }

    toast.success(
      "Perfil actualizado",
      `Se añadió: ${deltas.join(", ")}`
    );
  }, [summary]);
}
