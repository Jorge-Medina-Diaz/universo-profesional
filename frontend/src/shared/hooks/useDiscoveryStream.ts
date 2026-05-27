/**
 * Real-time discovery stream via SSE (Server-Sent Events).
 *
 * Wraps a fetch-based streaming reader so we can send the
 * Authorization header required by the backend endpoint.
 * Automatically reconnects with exponential backoff.
 */
import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/shared/api";
import { graphApi, type DiscoveryStreamEvent } from "@/graph/api";
import { toast } from "@/ui";
import { queryKeys } from "@/shared/queryKeys";

const INITIAL_RECONNECT_DELAY = 2000;
const MAX_RECONNECT_DELAY = 30000;

export function useDiscoveryStream(enabled = true) {
  const queryClient = useQueryClient();
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelay = useRef(INITIAL_RECONNECT_DELAY);

  useEffect(() => {
    if (!enabled) return;

    const token = useAuthStore.getState().accessToken;
    if (!token) return;

    let alive = true;

    const connect = async () => {
      try {
        const resp = await fetch(graphApi.discoveryStreamURL, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!resp.ok) {
          throw new Error(`HTTP ${resp.status}`);
        }
        if (!resp.body) {
          throw new Error("No response body");
        }

        // Reset backoff on successful connection.
        reconnectDelay.current = INITIAL_RECONNECT_DELAY;

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (alive) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const evt = JSON.parse(line.slice(6)) as DiscoveryStreamEvent;
                if (evt.type === "entity_discovered") {
                  // Trigger snapshot refetch so the new node appears.
                  queryClient.invalidateQueries({ queryKey: queryKeys.graph.snapshot });
                  toast.success(
                    `¡Nueva ${evt.entity_type} descubierta!`,
                    evt.name,
                  );
                }
              } catch {
                /* ignore malformed SSE line */
              }
            }
          }
        }
      } catch {
        /* silent fail — polling fallback covers us */
      } finally {
        if (alive) {
          reconnectTimer.current = setTimeout(
            connect,
            reconnectDelay.current,
          );
          reconnectDelay.current = Math.min(
            reconnectDelay.current * 1.5,
            MAX_RECONNECT_DELAY,
          );
        }
      }
    };

    connect();

    return () => {
      alive = false;
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
    };
  }, [enabled, queryClient]);
}
