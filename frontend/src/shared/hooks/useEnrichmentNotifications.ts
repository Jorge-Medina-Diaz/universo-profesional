import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "@/ui";
import { api, useAuthStore } from "@/shared/api";
import { queryKeys } from "@/shared/queryKeys";

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
 * The SINGLE source of "new entities discovered" toasts (mounted once in
 * Layout, so it covers every page). useDiscoveryProgress and useDiscoveryStream
 * deliberately do NOT toast — they only feed the pill/graph — so one discovery
 * yields exactly one toast instead of two or three.
 *
 * Uses the SHARED summary query key so it reuses the cache Router/Layout warm
 * (no duplicate /summary fetch).
 */
export function useEnrichmentNotifications() {
  const lastCountsRef = useRef<Record<string, number> | null>(null);
  const isAuthed = !!useAuthStore((s) => s.accessToken);

  const { data: summary } = useQuery<UniverseSummary>({
    queryKey: queryKeys.universe.summary,
    queryFn: async () => {
      return api<UniverseSummary>("/api/v1/universe/summary");
    },
    enabled: isAuthed,
    refetchInterval: SUMMARY_POLL_INTERVAL,
    staleTime: 5_000,
    retry: 1,
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

    toast.success(
      "Perfil actualizado",
      `Se añadió: ${deltas.join(", ")}`
    );
  }, [summary]);
}
