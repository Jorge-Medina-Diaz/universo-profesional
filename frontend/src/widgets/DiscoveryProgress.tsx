/**
 * DiscoveryProgressPill — compact "universe vitality" pill for the app header.
 *
 * The full discovery card was merged into {@link UniverseProgress} (the single
 * sidebar "state of your universe" widget); only this header pill remains here.
 */
import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { useDiscoveryProgress } from "@/shared/hooks/useDiscoveryProgress";

export function DiscoveryProgressPill() {
  const { data } = useDiscoveryProgress();
  const [celebrating, setCelebrating] = useState(false);

  useEffect(() => {
    const handler = () => {
      setCelebrating(true);
      setTimeout(() => setCelebrating(false), 1500);
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
      className="flex items-center gap-2 rounded-full border border-hairline bg-surface px-2.5 py-1"
    >
      {is_alive && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-leaf opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-leaf" />
        </span>
      )}
      <span className="text-xs font-medium text-ink">{discovery_score}/100</span>
      <span className="text-[10px] text-stone">{total_entities} ent.</span>
    </motion.div>
  );
}
