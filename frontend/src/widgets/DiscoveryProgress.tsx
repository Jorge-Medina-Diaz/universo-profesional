import { useDiscoveryProgress } from "@/shared/hooks/useDiscoveryProgress";
import { cn } from "@/ui";
import { motion, AnimatePresence } from "motion/react";
import { Sparkles, Activity, TrendingUp, Zap } from "lucide-react";
import { useEffect, useState } from "react";

import { KIND_LABELS } from "@/shared/kindColors";

const SOURCE_LABELS: Record<string, string> = {
  agent_chat: "Chat",
  import: "Import",
  manual: "Manual",
  onboarding: "Onboarding",
};

export function DiscoveryProgress() {
  const { data, isLoading } = useDiscoveryProgress();

  if (isLoading || !data) {
    return (
      <div className="p-4 rounded-xl bg-surface border border-hairline animate-pulse">
        <div className="h-4 bg-muted/20 rounded w-2/3 mb-3" />
        <div className="h-8 bg-muted/20 rounded w-1/2 mb-3" />
        <div className="h-3 bg-muted/20 rounded w-full" />
      </div>
    );
  }

  const {
    discovery_score,
    score_breakdown,
    total_entities,
    is_alive,
    activity_last_24h,
    sparse_dimensions,
    sources_last_7d,
    recent_discoveries,
  } = data;

  const scoreColor =
    discovery_score >= 80
      ? "text-leaf"
      : discovery_score >= 50
        ? "text-sunbeam"
        : "text-stone";

  const scoreBg =
    discovery_score >= 80
      ? "bg-leaf/10"
      : discovery_score >= 50
        ? "bg-sunbeam/10"
        : "bg-stone/10";

  return (
    <div className="p-4 rounded-xl bg-surface border border-hairline space-y-4">
      {/* Header: score + vitality indicator */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-nova" aria-hidden="true" />
          <span className="text-sm font-medium text-ink">Universo en crecimiento</span>
        </div>
        <AnimatePresence>
          {is_alive && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-leaf/10 text-leaf text-xs font-medium"
              role="status"
              aria-live="polite"
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-leaf opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-leaf" />
              </span>
              Activo
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Big score */}
      <div className="flex items-center gap-4">
        <div
          className={cn(
            "relative w-16 h-16 rounded-full flex items-center justify-center",
            scoreBg
          )}
          aria-label={`Puntuación de descubrimiento: ${discovery_score} de 100`}
          role="img"
        >
          <svg className="w-16 h-16 -rotate-90" viewBox="0 0 36 36">
            <path
              className="text-muted/20"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
            />
            <path
              className={scoreColor}
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeDasharray={`${discovery_score}, 100`}
              strokeLinecap="round"
            />
          </svg>
          <span className={cn("absolute text-sm font-bold", scoreColor)}>
            {discovery_score}
          </span>
        </div>
        <div className="flex-1">
          <div className="text-xs text-stone mb-1">
            {total_entities} entidades descubiertas
          </div>
          <div className="flex gap-1 flex-wrap">
            {Object.entries(score_breakdown).map(([key, val]) => (
              <span
                key={key}
                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-canvas text-[10px] text-stone"
                title={`${key}: +${val}`}
              >
                {key === "recency" && <Activity size={10} />}
                {key === "diversity" && <TrendingUp size={10} />}
                {key === "esco" && <Zap size={10} />}
                +{val}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Recent activity mini-feed */}
      {recent_discoveries.length > 0 && (
        <div className="space-y-1.5" aria-live="polite" aria-atomic="false">
          <span className="text-xs font-medium text-stone">Últimas descubiertas</span>
          <div className="space-y-1">
            {recent_discoveries.slice(0, 3).map((d, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08 }}
                className="flex items-center gap-2 text-xs"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-nova flex-shrink-0" aria-hidden="true" />
                <span className="text-ink capitalize">
                  {KIND_LABELS[d.entity_type] || d.entity_type}
                </span>
                <span className="text-stone">
                  {SOURCE_LABELS[d.source] || d.source}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Sparse dimensions (gaps) */}
      {sparse_dimensions.length > 0 && (
        <div className="space-y-1.5">
          <span className="text-xs font-medium text-stone">Por explorar</span>
          <div className="flex flex-wrap gap-1">
            {sparse_dimensions.map((dim) => (
              <span
                key={dim}
                className="px-2 py-0.5 rounded-full bg-canvas border border-hairline text-[10px] text-stone"
              >
                {KIND_LABELS[dim] || dim}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Sources breakdown */}
      {Object.keys(sources_last_7d).length > 0 && (
        <div className="space-y-1.5">
          <span className="text-xs font-medium text-stone">Fuentes (7 días)</span>
          <div className="flex gap-2">
            {Object.entries(sources_last_7d).map(([source, count]) => (
              <div key={source} className="flex items-center gap-1 text-xs">
                <span className="w-2 h-2 rounded-full bg-nova/60" />
                <span className="text-stone">{SOURCE_LABELS[source] || source}</span>
                <span className="font-medium text-ink">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Activity last 24h */}
      {activity_last_24h > 0 && (
        <div className="pt-2 border-t border-hairline">
          <span className="text-[10px] text-stone">
            {activity_last_24h} cambio{activity_last_24h > 1 ? "s" : ""} en las últimas 24h
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * Compact pill version for nav bars or small spaces.
 */
export function DiscoveryProgressPill() {
  const { data } = useDiscoveryProgress();
  const [celebrating, setCelebrating] = useState(false);

  useEffect(() => {
    const handler = (_e: Event) => {
      setCelebrating(true);
      const timer = setTimeout(() => setCelebrating(false), 1500);
      // Clean up the timer if component unmounts or another celebration happens
      return () => clearTimeout(timer);
    };
    window.addEventListener("discovery:celebrate", handler);
    return () => window.removeEventListener("discovery:celebrate", handler);
  }, []);

  if (!data) return null;

  const { discovery_score, is_alive, total_entities } = data;

  return (
    <motion.div
      animate={
        celebrating
          ? {
              scale: [1, 1.15, 1],
              boxShadow: [
                "0 0 0 0 rgba(110, 206, 157, 0)",
                "0 0 0 8px rgba(110, 206, 157, 0.35)",
                "0 0 0 0 rgba(110, 206, 157, 0)",
              ],
            }
          : {}
      }
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-surface border border-hairline"
    >
      {is_alive && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-leaf opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-leaf" />
        </span>
      )}
      <span className="text-xs font-medium text-ink">{discovery_score}/100</span>
      <span className="text-[10px] text-stone">{total_entities} ent.</span>
    </motion.div>
  );
}
