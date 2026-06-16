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

const MAX_SILENT_FAILURES = 4; // ~ up to ~1min of backoff before we warn once

export function useDiscoveryStream(enabled = true) {
  const queryClient = useQueryClient();
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelay = useRef(INITIAL_RECONNECT_DELAY);
  const failures = useRef(0);
  const warned = useRef(false);

  useEffect(() => {
    if (!enabled) return;

    let alive = true;

    const connect = async () => {
      const token = useAuthStore.getState().accessToken;
      if (!token) return;

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

        // Reset backoff + failure tracking on successful connection.
        reconnectDelay.current = INITIAL_RECONNECT_DELAY;
        failures.current = 0;
        warned.current = false;

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
                  // Live signal only: refetch the snapshot so the new node
                  // appears on the graph. The toast is owned by
                  // useEnrichmentNotifications (single source — no double-toast).
                  queryClient.invalidateQueries({ queryKey: queryKeys.graph.snapshot });
                }
              } catch {
                /* ignore malformed SSE line */
              }
            }
          }
        }
      } catch {
        // The poll-based hooks still cover data, but a persistently dead live
        // stream must not be fully silent (see [[no-silent-errors]]): after a
        // few consecutive failures, warn the user ONCE.
        failures.current += 1;
        if (failures.current >= MAX_SILENT_FAILURES && !warned.current) {
          warned.current = true;
          toast.error(
            "Sin actualizaciones en vivo",
            "Se perdió la conexión en tiempo real con tu universo; reintentando en segundo plano.",
          );
        }
      } finally {
        if (alive && useAuthStore.getState().accessToken) {
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
