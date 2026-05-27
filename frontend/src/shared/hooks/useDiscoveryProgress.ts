import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { api } from "@/shared/api";
import { toast } from "@/ui";
import { queryKeys } from "@/shared/queryKeys";

export interface DiscoveryProgress {
  counts: Record<string, number>;
  total_entities: number;
  coverage: Record<string, number>;
  sparse_dimensions: string[];
  discovery_score: number;
  score_breakdown: {
    base: number;
    recency: number;
    diversity: number;
    esco: number;
  };
  recent_discoveries: Array<{
    entity_type: string;
    change_type: string;
    source: string;
    changed_at: string;
  }>;
  sources_last_7d: Record<string, number>;
  activity_last_24h: number;
  esco_links: Record<string, number>;
  kinds_present: number;
  last_activity_at: string | null;
  is_alive: boolean;
}

const POLL_INTERVAL = 8_000; // 8s — fast enough to feel "live"
const SIGNIFICANT_SCORE_JUMP = 5;

const ENTITY_TYPE_LABELS: Record<string, string> = {
  experience: "experiencia",
  education: "formación",
  skill: "skill",
  project: "proyecto",
  certification: "certificación",
  course: "curso",
  language: "idioma",
  achievement: "logro",
  interest: "interés",
};

function labelForEntityType(type: string): string {
  return ENTITY_TYPE_LABELS[type] || type;
}

/**
 * Dispatches a celebration event that the pill can listen to.
 */
function dispatchCelebration(score: number, delta: number) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("discovery:celebrate", {
      detail: { score, delta },
    }),
  );
}

/**
 * Polls the discovery progress endpoint so the UI reflects the
 * growing universe in near real-time.
 */
export function useDiscoveryProgress(enabled = true) {
  const prevDataRef = useRef<DiscoveryProgress | null>(null);

  const query = useQuery<DiscoveryProgress>({
    queryKey: queryKeys.agents.discovery.progress,
    queryFn: async () => {
      return api<DiscoveryProgress>("/api/v1/agents/discovery/progress");
    },
    refetchInterval: POLL_INTERVAL,
    staleTime: 4_000,
    enabled,
  });

  const data = query.data;

  useEffect(() => {
    if (!data) {
      prevDataRef.current = data ?? null;
      return;
    }

    const prev = prevDataRef.current;
    prevDataRef.current = data;

    if (!prev) return;

    // Detect new discoveries
    const prevKeys = new Set(
      prev.recent_discoveries.map((d) => `${d.entity_type}-${d.change_type}-${d.changed_at}`),
    );
    const newDiscoveries = data.recent_discoveries.filter(
      (d) => !prevKeys.has(`${d.entity_type}-${d.change_type}-${d.changed_at}`),
    );

    for (const discovery of newDiscoveries.slice(0, 3)) {
      const label = labelForEntityType(discovery.entity_type);
      toast.success(
        `¡Nueva ${label} descubierta!`,
        discovery.change_type === "skill"
          ? `${discovery.change_type} añadida`
          : `Añadida desde ${discovery.source}`,
      );
    }

    // Detect significant score jump
    const scoreDelta = data.discovery_score - prev.discovery_score;
    if (scoreDelta >= SIGNIFICANT_SCORE_JUMP) {
      toast.success(
        "🎉 ¡Universo en expansión!",
        `Tu score de descubrimiento subió ${scoreDelta} puntos`,
      );
      dispatchCelebration(data.discovery_score, scoreDelta);
    }
  }, [data]);

  return query;
}
